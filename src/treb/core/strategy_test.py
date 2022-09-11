import typing

import pytest
from attrs import define
from testfixtures import ShouldRaise, compare

from treb.core.address import Address
from treb.core.artifact import Artifact, ArtifactSpec
from treb.core.check import Check
from treb.core.resource import Resource, ResourceSpec
from treb.core.step import Step
from treb.core.strategy import extract_addresses, is_addressable_type, istype, make_address


def test_is_addressable_type__returns_true_for_artifact_spec():
    @define(frozen=True, kw_only=True)
    class DummyArtifact(ArtifactSpec):
        @classmethod
        def spec_name(self) -> str:
            return "dummy"

        def exists(self, revision: str) -> bool:
            return True

    res = is_addressable_type(DummyArtifact)

    compare(res, True)


def test_is_addressable_type__returns_true_for_step():
    @define(frozen=True, kw_only=True)
    class DummyStep(Step):
        @classmethod
        def spec_name(self) -> str:
            return "dummy"

        def run(self, ctx):
            pass

        def rollback(self, ctx):
            pass

    res = is_addressable_type(DummyStep)

    compare(res, True)


def test_is_addressable_type__returns_true_for_resource():
    @define(frozen=True, kw_only=True)
    class DummyResource(ResourceSpec):
        @classmethod
        def spec_name(self) -> str:
            return "dummy"

    res = is_addressable_type(DummyResource)

    compare(res, True)


def test_is_addressable_type__returns_true_for_check():
    @define(frozen=True, kw_only=True)
    class DummyCheck(Check):
        @classmethod
        def spec_name(self) -> str:
            return "dummy"

        def check(self, ctx):
            pass

    res = is_addressable_type(DummyCheck)

    compare(res, True)


def test_is_addressable_type__returns_false_for_artifact():
    @define(frozen=True, kw_only=True)
    class DummyArtifact(Artifact):
        @classmethod
        def spec_name(self) -> str:
            return "dummy"

    res = is_addressable_type(DummyArtifact)

    compare(res, False)


def test_is_addressable_type__returns_false_for_resource():
    @define(frozen=True, kw_only=True)
    class DummyResource(Resource):
        @classmethod
        def spec_name(self) -> str:
            return "dummy"

    res = is_addressable_type(DummyResource)

    compare(res, False)


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


@define(frozen=True, kw_only=True)
class ArtifactTest(ArtifactSpec):
    @classmethod
    def spec_name(self) -> str:
        return "dummy"


def test_extract_addresses__return_unchanged_address():
    res = extract_addresses(ArtifactTest, Address(base="foo", name="bar"), "root")

    compare(res, Address(base="foo", name="bar"))


def test_extract_addresses__transform_relative_string_into_address():
    res = extract_addresses(ArtifactTest, ":foo", "root")

    compare(res, Address(base="root", name="foo"))


def test_extract_addresses__transform_absolute_string_into_address():
    res = extract_addresses(ArtifactTest, "//foo:bar", "root")

    compare(res, Address(base="foo", name="bar"))


def test_extract_addresses__optional_with_valid_value_return_address():
    res = extract_addresses(typing.Optional[ArtifactTest], "//foo:bar", "root")

    compare(res, Address(base="foo", name="bar"))


def test_extract_addresses__transform_addresses_in_dict():
    res = extract_addresses(
        typing.Dict[str, ArtifactTest | typing.Dict[str, ArtifactTest]],
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
        typing.Dict[str, ArtifactTest | int], {"foo": "//foo:bar", "bar": 1}, "root"
    )

    compare(res, {"foo": Address(base="foo", name="bar"), "bar": 1})


def test_extract_addresses__transform_addresses_in_list():
    res = extract_addresses(typing.List[ArtifactTest], ["//foo:bar", ":bar"], "root")

    compare(res, [Address(base="foo", name="bar"), Address(base="root", name="bar")])


def test_extract_addresses__transform_addresses_in_list_ignore_non_address():
    res = extract_addresses(typing.List[int | ArtifactTest], [1, "//foo:bar", ":bar"], "root")

    compare(res, [1, Address(base="foo", name="bar"), Address(base="root", name="bar")])
