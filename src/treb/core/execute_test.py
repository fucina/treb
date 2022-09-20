from typing import Optional

import pytest
from attrs import define
from testfixtures import compare

from treb.core.address import Address
from treb.core.artifact import Artifact
from treb.core.check import Check, FailedCheck
from treb.core.config import Config, ProjectConfig, StateConfig
from treb.core.context import Context
from treb.core.execute import execute_plan
from treb.core.plan import Action, ActionState, ActionType, Plan, generate_plan
from treb.core.resource import Resource
from treb.core.step import Step
from treb.core.strategy import Strategy


class Dummy:
    pass


@define(frozen=True, kw_only=True)
class ArtifactTest(Artifact):
    @classmethod
    def spec_name(self) -> str:
        return "test_artifact"

    def resolve(self, ctx: Context) -> Dummy:
        return Dummy()


@define(frozen=True, kw_only=True)
class ResourceTest:

    foo: str


@define(frozen=True, kw_only=True)
class ResourceTestSpec(Resource):
    @classmethod
    def spec_name(self) -> str:
        return "test_resource"

    def state(self, ctx: Context) -> Optional[ResourceTest]:
        return ResourceTest(foo="bar")


@define(frozen=True, kw_only=True)
class StepTest(Step):

    artifact: ArtifactTest
    resource: ResourceTestSpec

    @classmethod
    def spec_name(self) -> str:
        return "test_step"

    def snapshot(self, ctx: "Context") -> None:
        return None

    def run(self, ctx: Context, snapshot: None) -> dict:
        return {"foo": "abc"}

    def rollback(self, ctx: Context, snapshot: None):
        pass


@define(frozen=True, kw_only=True)
class CheckTest(Check):

    resource: ResourceTestSpec
    fail: bool = False

    @classmethod
    def spec_name(self) -> str:
        return "test_check"

    def check(self, ctx: Context) -> dict:
        if self.fail:
            raise FailedCheck({"passed": False})

        return {"passed": True}


@pytest.fixture
def treb_context(tmp_path_factory) -> Context:
    state_path = tmp_path_factory.mktemp("state")
    proj_path = tmp_path_factory.mktemp("proj")

    config = Config(
        state=StateConfig(repo_path=str(state_path)),
        project=ProjectConfig(repo_path=str(proj_path)),
    )

    ctx = Context(
        config=config,
        revision="abc",
        specs={
            "test_step": StepTest,  # type: ignore
            "test_check": CheckTest,  # type: ignore
            "test_artifact": ArtifactTest,  # type: ignore
            "test_resource": ResourceTestSpec,  # type: ignore
        },
    )

    return ctx


def test_execute_plan__empty_plan_returns_empty_generator(treb_context):
    strategy = Strategy(treb_context)

    strategy.register_artifact("root", ArtifactTest(name="artifact"))
    strategy.register_step(
        "root", StepTest(name="step", artifact="//root:artifact", resource="//root:resource")
    )
    strategy.register_resource("root", ResourceTestSpec(name="resource"))
    strategy.register_check("root", CheckTest(name="check", resource="//root:resource"))

    execution = execute_plan(strategy, Plan(actions=[]))

    compare(list(execution), [])


def test_execute_plan__run_all_actions_successfully():
    strategy = Strategy(treb_context)

    strategy.register_artifact("root", ArtifactTest(name="artifact"))
    strategy.register_step(
        "root", StepTest(name="step", artifact="//root:artifact", resource="//root:resource")
    )
    strategy.register_resource("root", ResourceTestSpec(name="resource"))
    strategy.register_check(
        "root", CheckTest(name="check", resource="//root:resource", after=["//root:step"])
    )

    plan = generate_plan(
        strategy,
        list(strategy.artifacts().keys()),
    )

    res = list(execute_plan(strategy, plan))

    compare(
        res,
        [
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.IN_PROGRESS,
                        result=None,
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.PLANNED,
                        result=None,
                        error=None,
                    ),
                ]
            ),
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.DONE,
                        result={"foo": "abc"},
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.PLANNED,
                        result=None,
                        error=None,
                    ),
                ]
            ),
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.DONE,
                        result={"foo": "abc"},
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.IN_PROGRESS,
                        result=None,
                        error=None,
                    ),
                ]
            ),
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.DONE,
                        result={"foo": "abc"},
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.DONE,
                        result={"passed": True},
                        error=None,
                    ),
                ]
            ),
        ],
    )


def test_execute__fail_check_and_start_rollback():
    strategy = Strategy(treb_context)

    strategy.register_artifact("root", ArtifactTest(name="artifact"))
    strategy.register_step(
        "root", StepTest(name="step", artifact="//root:artifact", resource="//root:resource")
    )
    strategy.register_resource("root", ResourceTestSpec(name="resource"))
    strategy.register_check(
        "root",
        CheckTest(name="check", resource="//root:resource", fail=True, after=["//root:step"]),
    )
    strategy.register_step(
        "root",
        StepTest(
            name="final-step",
            artifact="//root:artifact",
            resource="//root:resource",
            after=["//root:check"],
        ),
    )

    plan = generate_plan(
        strategy,
        list(strategy.artifacts().keys()),
    )

    res = list(execute_plan(strategy, plan))

    compare(
        res,
        [
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.IN_PROGRESS,
                        result=None,
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.PLANNED,
                        result=None,
                        error=None,
                    ),
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="final-step"),
                        state=ActionState.PLANNED,
                        result=None,
                        error=None,
                    ),
                ]
            ),
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.DONE,
                        result={"foo": "abc"},
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.PLANNED,
                        result=None,
                        error=None,
                    ),
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="final-step"),
                        state=ActionState.PLANNED,
                        result=None,
                        error=None,
                    ),
                ]
            ),
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.DONE,
                        result={"foo": "abc"},
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.IN_PROGRESS,
                        result=None,
                        error=None,
                    ),
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="final-step"),
                        state=ActionState.PLANNED,
                        result=None,
                        error=None,
                    ),
                ]
            ),
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.DONE,
                        result={"foo": "abc"},
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.DONE,
                        result={"passed": False},
                        error=None,
                    ),
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="final-step"),
                        state=ActionState.CANCELLED,
                        result=None,
                        error=None,
                    ),
                    Action(
                        type=ActionType.ROLLBACK,
                        address=Address(base="root", name="step"),
                        state=ActionState.PLANNED,
                        result=None,
                        error=None,
                    ),
                ]
            ),
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.DONE,
                        result={"foo": "abc"},
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.DONE,
                        result={"passed": False},
                        error=None,
                    ),
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="final-step"),
                        state=ActionState.CANCELLED,
                        result=None,
                        error=None,
                    ),
                    Action(
                        type=ActionType.ROLLBACK,
                        address=Address(base="root", name="step"),
                        state=ActionState.IN_PROGRESS,
                        result=None,
                        error=None,
                    ),
                ]
            ),
            Plan(
                actions=[
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="step"),
                        state=ActionState.DONE,
                        result={"foo": "abc"},
                        error=None,
                    ),
                    Action(
                        type=ActionType.CHECK,
                        address=Address(base="root", name="check"),
                        state=ActionState.DONE,
                        result={"passed": False},
                        error=None,
                    ),
                    Action(
                        type=ActionType.RUN,
                        address=Address(base="root", name="final-step"),
                        state=ActionState.CANCELLED,
                        result=None,
                        error=None,
                    ),
                    Action(
                        type=ActionType.ROLLBACK,
                        address=Address(base="root", name="step"),
                        state=ActionState.DONE,
                        result=None,
                        error=None,
                    ),
                ]
            ),
        ],
    )
