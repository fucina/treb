import copy
import enum
import inspect
from collections import defaultdict
from typing import Dict, Iterator, List, Optional, Type

from attrs import define, evolve, fields
from cattrs import structure, unstructure

from treb.core.address import Address
from treb.core.artifact import Artifact, ArtifactSpec
from treb.core.step import Step


@define(frozen=True, kw_only=True)
class Node:

    address: Address
    item: ArtifactSpec | Step


@enum.unique
class ActionState(enum.Enum):

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


@define(frozen=True, kw_only=True)
class Action:

    address: Address
    state: ActionState
    result: Optional[Dict[str, str]]


@define(frozen=True, kw_only=True)
class Plan:

    actions: List[Action]


class Strategy:
    def __init__(self, ctx):
        self._ctx = ctx
        self._steps = {}
        self._artifacts = {}
        self._graph = defaultdict(list)
        self._rev_graph = defaultdict(dict)

    def register_artifact(self, path: str, artifact: Type[ArtifactSpec]):
        node = Node(
            address=Address(base=path, name=artifact.name),
            item=artifact,
        )
        self._artifacts[node.address] = node

    def register_step(self, path: str, step: Type[Step]):
        address = Address(base=path, name=step.name)

        for field in fields(type(step)):
            value = getattr(step, field.name)
            print(field.name, field.type, value, type(value))

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
            self._graph[value].append(node.address)
            self._rev_graph[node.address][field.name] = value

    def plan(self) -> Plan:
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
                    )
                )

                del steps[step_node.address]
                artifacts[step_node.address] = step_node

        return Plan(
            actions=actions,
        )

    def execute(self, plan: Plan) -> Iterator[Plan]:
        results = {}

        for idx, action in enumerate(plan.actions):
            step_node = self._steps[action.address]

            if action.state in (ActionState.NOT_STARTED, ActionState.IN_PROGRESS):
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

                print(f"executing action {step_node.address}")
                res = step.run(self._ctx)

                results[step_node.address] = res

                new_actions = copy.deepcopy(plan.actions)
                new_actions[idx] = evolve(action, state=ActionState.DONE, result=unstructure(res))

                plan = evolve(plan, actions=new_actions)

                yield plan

            elif action.state is ActionState.FAILED:
                pass

            elif action.state is ActionState.DONE:
                signature = inspect.signature(step_node.item.run)
                results[step_node.address] = structure(action.result, signature.return_annotation)

            elif ActionState.ROLLED_BACK:
                print(f"rolling back action {step_node.address}")
                step.rollback(self._ctx)

                new_actions = copy.deepcopy(plan.actions)
                new_actions[idx] = evolve(action, state=ActionState.ROLLED_BACK)

                plan = evolve(plan, actions=new_actions)

                yield plan

            else:
                raise ValueError("invalid plan")
