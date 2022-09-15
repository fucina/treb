import textwrap
import typing
from pathlib import Path

import pytest
from attrs import define
from testfixtures import ShouldRaise, compare

from treb.core.address import Address
from treb.core.artifact import Artifact
from treb.core.check import Check, FailedCheck
from treb.core.config import Config, ProjectConfig, StateConfig
from treb.core.context import Context
from treb.core.resource import Resource
from treb.core.step import Step
from treb.core.strategy import (
    Strategy,
    extract_addresses,
    is_addressable_type,
    istype,
    make_address,
    prepare_strategy,
)


class Dummy:
    pass


@define(frozen=True, kw_only=True)
class ArtifactTestSpec(Artifact):
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

    def state(self, ctx: Context) -> typing.Optional[ResourceTest]:
        return ResourceTest(foo="bar")


@define(frozen=True, kw_only=True)
class StepTest(Step):

    artifact: ArtifactTestSpec
    resource: ResourceTestSpec

    @classmethod
    def spec_name(self) -> str:
        return "test_step"

    def run(self, ctx: Context) -> ResourceTest:
        return ResourceTest(foo="abc")

    def rollback(self, ctx: Context):
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
            "test_artifact": ArtifactTestSpec,  # type: ignore
            "test_resource": ResourceTestSpec,  # type: ignore
        },
    )

    return ctx


def test_is_addressable_type__returns_true_for_artifact_spec():
    res = is_addressable_type(ArtifactTestSpec)

    compare(res, True)


def test_is_addressable_type__returns_true_for_step():
    res = is_addressable_type(StepTest)

    compare(res, True)


def test_is_addressable_type__returns_true_for_resource_spec():
    res = is_addressable_type(ResourceTestSpec)

    compare(res, True)


def test_is_addressable_type__returns_true_for_check():
    res = is_addressable_type(CheckTest)

    compare(res, True)


@pytest.mark.parametrize(
    ["obj"],
    [
        (None,),
        (1,),
        (["//address:list"],),
        ({"foo", "//address:dict"},),
    ],
)
def test_make_address__raises_TypeError_if_cannot_convert_object_into_address(obj):
    with ShouldRaise(TypeError):
        make_address(obj, "root")


def test_make_address__transform_valid_relative_address_string():
    res = make_address(":foo", "root")

    compare(res, Address(base="root", name="foo"))


def test_make_address__transform_valid_absolute_address_string():
    res = make_address("//foo:bar", "root")

    compare(res, Address(base="foo", name="bar"))


def test_make_address__return_unchanged_address():
    res = make_address(Address(base="foo", name="bar"), "root")

    compare(res, Address(base="foo", name="bar"))


def test_make_address__raises_ValueError_if_address_is_invalid():
    with ShouldRaise(ValueError):
        make_address("invalid", "root")


@pytest.mark.parametrize(
    ["arg"],
    [
        (typing.Union,),
        (typing.Union[int, str, bool],),
        (typing.Optional,),
        (typing.Optional[str],),
        (typing.Dict[str, int],),
        (typing.List[str],),
        (11,),
        ("string",),
    ],
)
def test_istype__returns_false_if_argument_is_not_a_class(arg):
    res = istype(arg, object)

    compare(res, False)


@pytest.mark.parametrize(
    ["cls", "class_or_tuple"],
    [
        (int, object),
        (bool, int),
        (float, object),
        (str, int),
        (str, (int, float)),
        (str, (object, int)),
        (int, (object, int)),
    ],
)
def test_istype__behave_same_as_subclass(cls, class_or_tuple):
    res = istype(cls, class_or_tuple)
    expected = issubclass(cls, class_or_tuple)

    compare(res, expected)


def test_extract_addresses__return_unchanged_address():
    res = extract_addresses(ArtifactTestSpec, Address(base="foo", name="bar"), "root")

    compare(res, Address(base="foo", name="bar"))


def test_extract_addresses__transform_relative_string_into_address():
    res = extract_addresses(ArtifactTestSpec, ":foo", "root")

    compare(res, Address(base="root", name="foo"))


def test_extract_addresses__transform_absolute_string_into_address():
    res = extract_addresses(ArtifactTestSpec, "//foo:bar", "root")

    compare(res, Address(base="foo", name="bar"))


def test_extract_addresses__optional_with_valid_value_return_address():
    res = extract_addresses(typing.Optional[ArtifactTestSpec], "//foo:bar", "root")

    compare(res, Address(base="foo", name="bar"))


def test_extract_addresses__optional_with_none_return_none():
    res = extract_addresses(typing.Optional[ArtifactTestSpec], None, "root")

    compare(res, None)


def test_extract_addresses__optional_dict_with_no_address_returns_none():
    res = extract_addresses(typing.Optional[typing.Dict[str, str]], None, "root")

    compare(res, None)


def test_extract_addresses__optional_dict_with_no_address_returns_dict():
    res = extract_addresses(typing.Optional[typing.Dict[str, str]], {"foo": "bar"}, "root")

    compare(res, {"foo": "bar"})


def test_extract_addresses__transform_addresses_in_dict():
    res = extract_addresses(
        typing.Dict[str, ArtifactTestSpec | typing.Dict[str, ArtifactTestSpec]],
        {"main": "//foo:bar", "nested": {"two": ":bar"}},
        "root",
    )

    compare(
        res,
        {
            "main": Address(base="foo", name="bar"),
            "nested": {"two": Address(base="root", name="bar")},
        },
    )


def test_extract_addresses__transform_addresses_in_dict_ignore_non_addres():
    res = extract_addresses(
        typing.Dict[str, ArtifactTestSpec | int], {"foo": "//foo:bar", "bar": 1}, "root"
    )

    compare(res, {"foo": Address(base="foo", name="bar"), "bar": 1})


def test_extract_addresses__transform_addresses_in_list():
    res = extract_addresses(typing.List[ArtifactTestSpec], ["//foo:bar", ":bar"], "root")

    compare(res, [Address(base="foo", name="bar"), Address(base="root", name="bar")])


def test_extract_addresses__transform_addresses_in_list_ignore_non_address():
    res = extract_addresses(typing.List[int | ArtifactTestSpec], [1, "//foo:bar", ":bar"], "root")

    compare(res, [1, Address(base="foo", name="bar"), Address(base="root", name="bar")])


def test_extract_addresses_raise_TypeError_if_value_does_not_match_type():
    with ShouldRaise(TypeError):
        extract_addresses(int, "foo", "root")


def test_prepare_strategy__no_deploy_file_return_empty_strategy(treb_context):
    res = prepare_strategy(treb_context)

    compare(res.specs(), {})


def test_prepare_strategy__register_specs_from_deploy_file(treb_context):
    with open(Path(treb_context.config.project.repo_path) / "DEPLOY", "w") as fp:
        fp.write(
            textwrap.dedent(
                """
        test_artifact(name="artifact")

        test_resource(name="resource")

        test_step(name="step", resource=":resource", artifact=":artifact")

        test_check(name="check", resource=":resource", after=[":step"])
        """
            )
        )

    res = prepare_strategy(treb_context)

    compare(
        res.specs(),
        {
            Address(base="", name="artifact"): ArtifactTestSpec(name="artifact"),
            Address(base="", name="resource"): ResourceTestSpec(name="resource"),
            Address(base="", name="step"): StepTest(
                name="step", resource=":resource", artifact=":artifact"
            ),
            Address(base="", name="check"): CheckTest(
                name="check", resource=":resource", after=[":step"]
            ),
        },
    )


def test_Strategy_dependencies__returns_spec_dependencies(treb_context):
    strategy = Strategy(treb_context)

    strategy.register_artifact("root", ArtifactTestSpec(name="artifact"))
    strategy.register_step(
        "root", StepTest(name="step", artifact="//root:artifact", resource="//root:resource")
    )
    strategy.register_resource("root", ResourceTestSpec(name="resource"))
    strategy.register_check("root", CheckTest(name="check", resource="//root:resource"))

    compare(strategy.dependencies(Address(base="root", name="artifact")), {})
    compare(
        strategy.dependencies(Address(base="root", name="step")),
        {
            "artifact": Address(base="root", name="artifact"),
            "resource": Address(base="root", name="resource"),
            "after": [],
        },
    )
    compare(strategy.dependencies(Address(base="root", name="resource")), {})
    compare(
        strategy.dependencies(Address(base="root", name="check")),
        {"resource": Address(base="root", name="resource"), "after": [], "fail": False},
    )
