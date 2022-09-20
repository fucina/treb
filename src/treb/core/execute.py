"""Rules for planning and executing a treb deploy strategy."""
import copy
import inspect
from typing import Any, Dict, Iterable, Tuple, cast

from attrs import evolve
from cattrs import structure, unstructure

from treb.core.address import Address
from treb.core.check import Check, FailedCheck
from treb.core.plan import Action, ActionState, ActionType, Plan, resolve_addresses
from treb.core.step import Step
from treb.core.strategy import Strategy
from treb.utils import error, print_waiting, rollback, success


def _execute_plan_planned(strategy: Strategy, plan: Plan, action_idx: int, results) -> Plan:
    action = plan.actions[action_idx]
    new_action = evolve(
        action,
        state=ActionState.IN_PROGRESS,
    )

    if action.type is ActionType.RUN:
        action = plan.actions[action_idx]
        new_actions = copy.deepcopy(plan.actions)

        step = strategy.steps().get(action.address)
        if step is None:
            raise ValueError(f"step {action.address} does not exist")

        if not isinstance(step, Step):
            raise TypeError(f"node {action.address} is not a step")

        dep_artifacts = resolve_addresses(
            strategy.dependencies(action.address),
            results,
        )
        item = evolve(step, **dep_artifacts)

        snapshot = item.snapshot(strategy.ctx())
        new_action = evolve(new_action, snapshot=unstructure(snapshot))

    new_actions = copy.deepcopy(plan.actions)
    new_actions[action_idx] = new_action

    return evolve(plan, actions=new_actions)


def _perform_run(strategy: Strategy, address: Address, snapshot, step: Step, results):
    dep_artifacts = resolve_addresses(
        strategy.dependencies(address),
        results,
    )
    item = evolve(step, **dep_artifacts)

    if isinstance(step, Step):
        decoded_snapshot = structure(snapshot, inspect.signature(item.snapshot).return_annotation)

    else:
        decoded_snapshot = None

    res = None

    with print_waiting(f"step {address}"):
        res = item.run(strategy.ctx(), decoded_snapshot)
        success(f"step completed address={address}")

    return res


def _perform_check(strategy: Strategy, address: Address, check: Check, results):
    dep_artifacts = resolve_addresses(
        strategy.dependencies(address),
        results,
    )

    check = evolve(check, **dep_artifacts)

    try:
        with print_waiting(f"check {address}"):
            res = check.check(strategy.ctx())

    except FailedCheck:
        error(f"check failed address={address}")
        raise

    else:
        success(f"check passed address={address}")

    return res


def _perform_rollback(strategy: Strategy, address: Address, snapshot, step: Step, results):
    dep_artifacts = resolve_addresses(
        strategy.dependencies(address),
        results,
    )
    item = evolve(step, **dep_artifacts)

    decoded_snapshot = structure(inspect.signature(item.snapshot).return_annotation, snapshot)

    with print_waiting(f"rollback {address}"):
        res = item.rollback(strategy.ctx(), decoded_snapshot)

        rollback(
            f"rolled back address={address}",
        )

    return res


def _execute_plan_in_progress(
    strategy: Strategy, plan: Plan, action_idx: int, results
) -> Tuple[Plan, bool]:
    action = plan.actions[action_idx]
    spec = strategy.specs().get(action.address)
    new_actions = copy.deepcopy(plan.actions)
    results = copy.deepcopy(results)

    start_rollback = False

    if spec is None:
        raise Exception(f"action's spec not found: {action}")

    try:
        match action.type:
            case ActionType.RUN:
                res = _perform_run(
                    strategy,
                    action.address,
                    action.snapshot,
                    cast(Step, spec),
                    results,
                )

            case ActionType.ROLLBACK:
                res = _perform_rollback(
                    strategy,
                    action.address,
                    action.snapshot,
                    cast(Step, spec),
                    results,
                )

            case ActionType.CHECK:
                res = _perform_check(
                    strategy,
                    action.address,
                    cast(Check, spec),
                    results,
                )

            case _:
                raise ValueError(f"unexpected action type {action.type}")

        new_action = evolve(action, state=ActionState.DONE, result=res)

    except FailedCheck as exc:
        new_action = evolve(action, state=ActionState.DONE, result=exc.result)
        start_rollback = action.state is not ActionType.ROLLBACK

    new_actions[action_idx] = new_action
    plan = evolve(plan, actions=new_actions)

    return plan, start_rollback


def execute_plan(strategy: Strategy, plan: Plan) -> Iterable[Plan]:
    """Executes a plan performing each action sequentially and yielding a new
    version of the plan for each state change.

    The yielded plan is a copy of the original plan.

    Arguments:
        plan: the plan to execute.

    Yields:
        A new state of the after each action state change.
    """
    results: Dict[Address, Any] = {
        addr: art.resolve(strategy.ctx())
        for addr, art in strategy.artifacts().items()
        if art.exists(strategy.ctx())
    } | strategy.resources()

    idx = 0

    while True:
        if idx >= len(plan.actions):
            break

        action = plan.actions[idx]

        match action.state:
            case ActionState.PLANNED:
                plan = _execute_plan_planned(strategy, plan, idx, results)

                yield plan

            case ActionState.IN_PROGRESS:
                plan, start_rollback = _execute_plan_in_progress(strategy, plan, idx, results)

                results[action.address] = plan.actions[idx].result

                if start_rollback:
                    done_actions = plan.actions[: idx + 1]
                    cancelled_actions = []
                    rollback_actions = []

                    for planned_action in plan.actions[idx + 1 :]:
                        cancelled_actions.append(
                            evolve(planned_action, state=ActionState.CANCELLED)
                        )

                    for done_action in reversed(done_actions):
                        if done_action.type is ActionType.RUN:
                            rollback_actions.append(
                                Action(
                                    type=ActionType.ROLLBACK,
                                    address=done_action.address,
                                    state=ActionState.PLANNED,
                                    result=None,
                                    error=None,
                                )
                            )
                    plan = evolve(plan, actions=done_actions + cancelled_actions + rollback_actions)

                yield plan

                idx += 1

            case ActionState.FAILED | ActionState.DONE | ActionState.CANCELLED:
                idx += 1

            case _:
                raise ValueError(f"unexpected action state {action.state}")
