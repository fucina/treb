"""Rules for planning and executing a treb deploy strategy."""
import copy
import functools
import inspect
import os
from collections import defaultdict
from typing import Iterable, Type

from attrs import define, evolve, fields
from cattrs import structure, unstructure

from treb.core.address import Address
from treb.core.artifact import Artifact, ArtifactSpec
from treb.core.context import Context
from treb.core.deploy import discover_deploy_files
from treb.core.plan import Action, ActionState, Plan
from treb.core.step import Step


@define(frozen=True, kw_only=True)
class Node:
    """Represents a node in the strategy graph.

    Arguments:
        address: the node address.
        item: the actual node that can be wither a step or an artifact.
    """

    address: Address
    item: ArtifactSpec | Step


class Strategy:
    """Describes the deploy strategy for a project.

    Arguments:
        ctx: the context where to execute the deploy strategy.
    """

    def __init__(self, ctx):
        self._ctx = ctx
        self._steps = {}
        self._artifacts = {}
        self._rev_graph = defaultdict(dict)

    def register_artifact(self, path: str, artifact: Type[ArtifactSpec]):
        """Adds an artifact to the deploy strategy.

        Arguments:
            path: the base path to the artifact definition.
            artifact: the artifact spec to add.
        """
        node = Node(
            address=Address(base=path, name=artifact.name),
            item=artifact,
        )
        self._artifacts[node.address] = node

    def register_step(self, path: str, step: Type[Step]):
        """Adds a step to the deploy strategy.

        Arguments:
            path: the base path to the step definition.
            artifact: the artifact spec to add.
        """
        address = Address(base=path, name=step.name)

        for field in fields(type(step)):
            value = getattr(step, field.name)

            if not issubclass(field.type, (Artifact, ArtifactSpec, Step)):
                continue

            if isinstance(value, str):
                value = Address.from_string(path, value)

            if not isinstance(value, Address):
                raise TypeError("reference to steps or artifacts must be a valid address")

            node = Node(
                address=address,
                item=step,
            )

            self._steps[address] = node
            self._rev_graph[node.address][field.name] = value

    def plan(self) -> Plan:
        """Generates a new plan for the deployment strategy."""
        steps = copy.deepcopy(self._steps)
        artifacts = copy.deepcopy(self._artifacts)

        if not artifacts:
            raise ValueError("no artifacts defined")

        actions = []

        while steps:
            for step_node in list(steps.values()):
                dep_addresses = self._rev_graph[step_node.address]
                dep_artifacts = {
                    name: artifacts[addr].item
                    for name, addr in dep_addresses.items()
                    if addr in artifacts
                }

                if len(dep_addresses) != len(dep_artifacts):
                    continue

                actions.append(
                    Action(
                        address=step_node.address,
                        state=ActionState.NOT_STARTED,
                        result=None,
                        error=None,
                    )
                )

                del steps[step_node.address]
                artifacts[step_node.address] = step_node

        return Plan(
            actions=actions,
        )

    def _run_action(self, step_node: Node, results):
        dep_addresses = self._rev_graph[step_node.address]
        dep_artifacts = {}
        for name, addr in dep_addresses.items():
            if addr in results:
                dep_artifacts[name] = results[addr]
            elif addr in self._artifacts:
                dep_artifacts[name] = self._artifacts[addr].item
            else:
                raise ValueError("invalid plan")

        step = evolve(step_node.item, **dep_artifacts)

        res = step.run(self._ctx)

        return res

    def _rollback_action(self, step_node: Node):
        print(f"rolling back action {step_node.address}")
        step_node.item.rollback(self._ctx)

    def execute(self, plan: Plan) -> Iterable[Plan]:
        """Executes a plan performing each action sequentially and yielding a
        new version of the plan for each state change.

        The yielded plan is a copy of the original plan.

        Arguments:
            plan: the plan to execute.

        Yields:
            A new state of the after each action state change.
        """
        results = {}

        for idx, action in enumerate(plan.actions):
            step_node = self._steps[action.address]

            match action.state:
                case ActionState.NOT_STARTED | ActionState.IN_PROGRESS:
                    res = self._run_action(step_node, results)

                    results[step_node.address] = res

                    new_actions = copy.deepcopy(plan.actions)
                    new_actions[idx] = evolve(
                        action, state=ActionState.DONE, result=unstructure(res)
                    )

                    plan = evolve(plan, actions=new_actions)

                    yield plan

                case ActionState.ERRORED | ActionState.ROLLING_BACK:
                    self._rollback_action(step_node)

                    new_actions = copy.deepcopy(plan.actions)
                    new_actions[idx] = evolve(action, state=ActionState.FAILED)

                    plan = evolve(plan, actions=new_actions)

                    yield plan

                case ActionState.DONE:
                    signature = inspect.signature(step_node.item.run)
                    results[step_node.address] = structure(
                        action.result, signature.return_annotation
                    )

                case ActionState.FAILED:
                    pass

                case _:
                    raise ValueError("invalid plan")


def prepare_strategy(ctx: Context) -> Strategy:
    """Generates the strategy from the defintions found in the deploy files.

    Arguments:
        ctx: the context used to generate the strategy.

    Returns:
        The strategy for the given repo.
    """
    strategy = Strategy(ctx)

    def _register_step(base, step):
        return strategy.register_step(base, step)

    def _register_artifact(base, artifact):
        strategy.register_artifact(base, artifact)

    for deploy_file in discover_deploy_files(
        root=ctx.config.project.repo_path, deploy_filename=ctx.config.deploy_filename
    ):
        base = os.path.normpath(os.path.dirname(deploy_file.path))

        register_step = functools.partial(_register_step, base)
        register_artifact = functools.partial(_register_artifact, base)

        Step.register_callback(register_step)
        ArtifactSpec.register_callback(register_artifact)

        exec_globals = {**ctx.artifact_specs}

        exec(  # nosec[B102:exec_used] pylint: disable=exec-used
            deploy_file.code,
            exec_globals,
        )

        Step.unregister_callback(register_step)
        ArtifactSpec.unregister_callback(register_artifact)

    return strategy
