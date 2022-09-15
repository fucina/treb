from typing import Optional

import pytest
from attrs import define
from testfixtures import ShouldRaise, compare

from treb.core.address import Address
from treb.core.artifact import Artifact
from treb.core.check import Check
from treb.core.config import Config, ProjectConfig, StateConfig
from treb.core.context import Context
from treb.core.plan import (
    Action,
    ActionType,
    Plan,
    UnknownAddresses,
    UnresolvableAddress,
    generate_plan,
    resolve_addresses,
)
from treb.core.resource import Resource
from treb.core.step import Step
from treb.core.strategy import Strategy


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
    )

    return ctx


def test_resolve_addresses__single_resolvable_address_returns_mapped_value():
    res = resolve_addresses(
        {Address(base="a", name="b"): 1, Address(base="c", name="d"): "spam"},
        Address(base="a", name="b"),
    )

    compare(res, 1)


def test_resolve_addresses__single_unresolvable_address_raises_UnresolvableAddress():
    with ShouldRaise(UnresolvableAddress) as exc:
        resolve_addresses(
            {Address(base="a", name="b"): 1, Address(base="c", name="d"): "spam"},
            Address(base="not", name="found"),
        )

    compare(exc.raised.address, Address(base="not", name="found"))


def test_resolve_addresses__single_resolvable_address_with_attr_returns_mapped_value():
    @define
    class Data:
        x: int
        y: float

    mapping = {Address(base="a", name="b"): Data(x=1, y=2.3)}

    res = resolve_addresses(
        mapping,
        Address(base="a", name="b", attr="x"),
    )

    compare(res, 1)

    res = resolve_addresses(
        mapping,
        Address(base="a", name="b", attr="y"),
    )

    compare(res, 2.3)


def test_resolve_addresses__single_resolvable_address_with_nested_attr_returns_mapped_value():
    @define
    class Nested:
        y: str

    @define
    class Data:
        x: int
        y: float
        nested: Nested

    mapping = {Address(base="a", name="b"): Data(x=1, y=2.3, nested=Nested(y="foo"))}

    res = resolve_addresses(
        mapping,
        Address(base="a", name="b", attr="nested"),
    )

    compare(res, Nested(y="foo"))

    res = resolve_addresses(
        mapping,
        Address(base="a", name="b", attr="nested.y"),
    )

    compare(res, "foo")

    res = resolve_addresses(
        mapping,
        Address(base="a", name="b", attr="x"),
    )

    compare(res, 1)

    res = resolve_addresses(
        mapping,
        Address(base="a", name="b", attr="y"),
    )

    compare(res, 2.3)


def test_resolve_addresses__empty_dict_returns_empty_dict():
    res = resolve_addresses(
        {Address(base="a", name="b"): 1, Address(base="c", name="d"): "spam"}, {}
    )

    compare(res, {})


def test_resolve_addresses__non_empty_dict_without_addresses_returns_same_dict():
    res = resolve_addresses(
        {Address(base="a", name="b"): 1, Address(base="c", name="d"): "spam"},
        {"foo": 1, "spam": "bar"},
    )

    compare(res, {"foo": 1, "spam": "bar"})


def test_resolve_addresses__replace_addresses_in_dict_with_their_mapped_value():
    res = resolve_addresses(
        {
            Address(base="a", name="b"): 11,
            Address(base="c", name="d"): "spam",
            Address(base="e", name="f"): "hi",
        },
        {
            "foo": Address(base="a", name="b"),
            "bar": Address(base="a", name="b"),
            "spam": Address(base="c", name="d"),
            "other": 1,
        },
    )

    compare(res, {"foo": 11, "bar": 11, "spam": "spam", "other": 1})


def test_resolve_addresses__replace_addresses_in_nested_dicts():
    res = resolve_addresses(
        {
            Address(base="a", name="b"): 11,
            Address(base="c", name="d"): "spam",
            Address(base="e", name="f"): "hi",
        },
        {
            "foo": Address(base="a", name="b"),
            "nested": {"bar": Address(base="a", name="b"), "spam": Address(base="c", name="d")},
            "other": 1,
        },
    )

    compare(res, {"foo": 11, "nested": {"bar": 11, "spam": "spam"}, "other": 1})


def test_resolve_addresses__raises_UnresolvableAddress_when_address_in_dict_cannot_be_resolved():
    with ShouldRaise(UnresolvableAddress) as exc:
        resolve_addresses(
            {
                Address(base="a", name="b"): 11,
                Address(base="c", name="d"): "spam",
                Address(base="e", name="f"): "hi",
            },
            {
                "foo": Address(base="a", name="b"),
                "bar": Address(base="a", name="b"),
                "spam": Address(base="not", name="found"),
                "other": 1,
            },
        )

    compare(exc.raised.address, Address(base="not", name="found"))


def test_resolve_addresses__raises_UnresolvableAddress_if_address_cannot_resolve_nested_dict():
    with ShouldRaise(UnresolvableAddress) as exc:
        resolve_addresses(
            {
                Address(base="a", name="b"): 11,
                Address(base="c", name="d"): "spam",
            },
            {
                "foo": Address(base="a", name="b"),
                "bar": {
                    "spam": Address(base="not", name="found"),
                    "other": 1,
                },
            },
        )

    compare(exc.raised.address, Address(base="not", name="found"))


def test_resolve_addresses__empty_list():
    res = resolve_addresses(
        {
            Address(base="a", name="b"): "bar",
            Address(base="c", name="d"): "other",
        },
        [],
    )

    compare(res, [])


def test_resolve_addresses__return_unchanged_list_if_it_does_not_contain_addresses():
    res = resolve_addresses(
        {
            Address(base="c", name="d"): "other",
        },
        [
            "foo",
            "bar",
        ],
    )

    compare(res, ["foo", "bar"])


def test_resolve_addresses__replace_addresses_in_list():
    res = resolve_addresses(
        {
            Address(base="a", name="b"): "bar",
            Address(base="c", name="d"): "other",
        },
        [
            "foo",
            Address(base="a", name="b"),
            "spam",
            Address(base="c", name="d"),
        ],
    )

    compare(res, ["foo", "bar", "spam", "other"])


def test_resolve_addresses__raises_UnresolvableAddress_when_address_in_list_cannot_be_resolved():
    with ShouldRaise(UnresolvableAddress) as exc:
        resolve_addresses(
            {
                Address(base="a", name="b"): 11,
                Address(base="c", name="d"): "spam",
            },
            [
                Address(base="a", name="b"),
                Address(base="not", name="found"),
            ],
        )

    compare(exc.raised.address, Address(base="not", name="found"))


class Dummy:
    pass


@define(frozen=True, kw_only=True)
class DummyArtifact(Artifact):
    @classmethod
    def spec_name(self) -> str:
        return "dummy_artifact"

    def resolve(self, ctx: Context) -> Optional[Dummy]:
        return Dummy()


@define(frozen=True, kw_only=True)
class DummyResource:
    pass


@define(frozen=True, kw_only=True)
class DummyResourceSpec(Resource):
    @classmethod
    def spec_name(self) -> str:
        return "dummy_resource"

    def state(self, ctx: Context) -> Optional[DummyResource]:
        return DummyResource()


@define(frozen=True, kw_only=True)
class DummyStep(Step):

    artifact: DummyArtifact
    resource: Optional[DummyResourceSpec] = None

    @classmethod
    def spec_name(self) -> str:
        return "dummy_step"

    def run(self, ctx: Context) -> None:
        return None

    def rollback(self, ctx: Context):
        pass


@define(frozen=True, kw_only=True)
class DummyCheck(Check):

    resource: DummyResourceSpec

    @classmethod
    def spec_name(self) -> str:
        return "dummy_check"

    def check(self, ctx: Context):
        pass


def test_generate_plan__empty_strategy_generates_empty_plan(treb_context):
    strategy = Strategy(ctx=treb_context)
    available_artifacts = list(strategy.artifacts().keys())

    res = generate_plan(
        strategy,
        available_artifacts,
    )

    compare(res, Plan(actions=[]))


def test_generate_plan__strategy_with_single_artifact_generates_empty_plan(treb_context):
    strategy = Strategy(ctx=treb_context)
    strategy.register_artifact("root", DummyArtifact(name="artifact"))

    available_artifacts = list(strategy.artifacts().keys())

    res = generate_plan(
        strategy,
        available_artifacts,
    )

    compare(res, Plan(actions=[]))


def test_generate_plan__strategy_with_step_generates_single_action(treb_context):
    strategy = Strategy(ctx=treb_context)
    strategy.register_artifact("root", DummyArtifact(name="artifact"))
    strategy.register_step("root", DummyStep(name="step", artifact="//root:artifact"))

    available_artifacts = list(strategy.artifacts().keys())

    res = generate_plan(
        strategy,
        available_artifacts,
    )

    compare(
        res,
        Plan(
            actions=[
                Action(type=ActionType.RUN, address=Address(base="root", name="step")),
            ]
        ),
    )


def test_generate_plan__strategy_with_two_indipendent_steps_generates_two_actions(treb_context):
    strategy = Strategy(ctx=treb_context)
    strategy.register_artifact("root", DummyArtifact(name="artifact"))
    strategy.register_step("root", DummyStep(name="step-foo", artifact="//root:artifact"))
    strategy.register_step("root", DummyStep(name="step-bar", artifact="//root:artifact"))

    available_artifacts = list(strategy.artifacts().keys())

    res = generate_plan(
        strategy,
        available_artifacts,
    )

    compare(
        res,
        Plan(
            actions=[
                Action(type=ActionType.RUN, address=Address(base="root", name="step-bar")),
                Action(type=ActionType.RUN, address=Address(base="root", name="step-foo")),
            ]
        ),
    )


def test_generate_plan__strategy_with_dependent_steps_generates_all_actions_in_order(treb_context):
    strategy = Strategy(ctx=treb_context)
    strategy.register_artifact("root", DummyArtifact(name="artifact"))
    strategy.register_step(
        "root", DummyStep(name="step-three", artifact="//root:artifact", after=["//root:step-two"])
    )
    strategy.register_step("root", DummyStep(name="step-one", artifact="//root:artifact"))
    strategy.register_step(
        "root", DummyStep(name="step-two", artifact="//root:artifact", after=["//root:step-one"])
    )

    available_artifacts = list(strategy.artifacts().keys())

    res = generate_plan(
        strategy,
        available_artifacts,
    )

    compare(
        res,
        Plan(
            actions=[
                Action(type=ActionType.RUN, address=Address(base="root", name="step-one")),
                Action(type=ActionType.RUN, address=Address(base="root", name="step-two")),
                Action(type=ActionType.RUN, address=Address(base="root", name="step-three")),
            ]
        ),
    )


def test_generate_plan__can_generate_actions_for_all_specs(treb_context):
    strategy = Strategy(ctx=treb_context)
    strategy.register_check("root", DummyCheck(name="check", resource="//root:step"))
    strategy.register_step(
        "root", DummyStep(name="step", artifact="//root:artifact", resource="//root:resource")
    )
    strategy.register_resource("root", DummyResourceSpec(name="resource"))
    strategy.register_artifact("root", DummyArtifact(name="artifact"))

    available_artifacts = list(strategy.artifacts().keys())

    res = generate_plan(
        strategy,
        available_artifacts,
    )

    compare(
        res,
        Plan(
            actions=[
                Action(type=ActionType.RUN, address=Address(base="root", name="step")),
                Action(type=ActionType.CHECK, address=Address(base="root", name="check")),
            ]
        ),
    )


def test_generate_plan__can_generate_plan_for_diamond_shaped_dependencies(treb_context):
    strategy = Strategy(ctx=treb_context)
    strategy.register_artifact("root", DummyArtifact(name="artifact"))
    strategy.register_step("root", DummyStep(name="step-foo", artifact="//root:artifact"))
    strategy.register_step("root", DummyStep(name="step-bar", artifact="//root:artifact"))
    strategy.register_check(
        "root", DummyCheck(name="check", resource="//root:step-foo", after=["//root:step-bar"])
    )

    available_artifacts = list(strategy.artifacts().keys())

    res = generate_plan(
        strategy,
        available_artifacts,
    )

    compare(
        res,
        Plan(
            actions=[
                Action(type=ActionType.RUN, address=Address(base="root", name="step-bar")),
                Action(type=ActionType.RUN, address=Address(base="root", name="step-foo")),
                Action(type=ActionType.CHECK, address=Address(base="root", name="check")),
            ]
        ),
    )


def test_generate_plan__raise_AddressNotFound_if_nodes_use_unknown_addresses(treb_context):
    strategy = Strategy(ctx=treb_context)
    strategy.register_artifact("root", DummyArtifact(name="artifact"))
    strategy.register_step("root", DummyStep(name="step-foo", artifact="//root:not-found"))
    strategy.register_check("root", DummyCheck(name="check", resource="//root:impossible"))

    available_artifacts = list(strategy.artifacts().keys())

    with ShouldRaise(UnknownAddresses) as exc:
        generate_plan(
            strategy,
            available_artifacts,
        )

    compare(
        exc.raised.addresses,
        [
            Address(base="root", name="impossible"),
            Address(base="root", name="not-found"),
        ],
    )
