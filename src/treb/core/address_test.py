import pytest
from testfixtures import ShouldRaise, compare

from treb.core.address import Address, is_valid_name


@pytest.mark.parametrize(
    ["name"],
    [
        (":abc",),
        ("abc:",),
        ("9abc",),
        ("abc-",),
        ("-abc",),
        ("-abc-",),
        ("",),
    ],
)
def test_is_valid_name__return_false_for_invalid_name(name):
    res = is_valid_name(name)

    compare(res, False)


@pytest.mark.parametrize(
    ["name"],
    [
        ("abc",),
        ("abc123",),
        ("abc-123",),
    ],
)
def test_is_valid_name__return_true_for_valid_name(name):
    res = is_valid_name(name)

    compare(res, True)


@pytest.mark.parametrize(
    ["base", "name"],
    [
        ("foo", ":bar"),
        ("foo", "9abc"),
        ("foo", "abc-"),
        ("foo", "-abc"),
        ("foo", "-abc-"),
        ("foo", ""),
    ],
)
def test_Address__raises_ValueError_if_invalid(base, name):
    with ShouldRaise(ValueError):
        Address(base=base, name=name)


@pytest.mark.parametrize(
    ["base", "name", "expected"],
    [
        ("foo", "bar", "//foo:bar"),
        ("foo/bar", "spam", "//foo/bar:spam"),
    ],
)
def test_Address__stringify_an_address(base, name, expected):
    addr = Address(base=base, name=name)

    compare(str(addr), expected)


@pytest.mark.parametrize(
    ["base", "address", "expected_base", "expected_name"],
    [
        ("foo", "//foo:bar", "foo", "bar"),
        ("foo", "//foo/bar:spam", "foo/bar", "spam"),
        ("other", "//foo/bar:spam", "foo/bar", "spam"),
    ],
)
def test_Address_from_address__parse_absolute_address(base, address, expected_base, expected_name):
    addr = Address.from_string(base, address)

    compare(addr, Address(base=expected_base, name=expected_name))


@pytest.mark.parametrize(
    ["base", "address", "expected_base", "expected_name"],
    [
        ("foo", ":bar", "foo", "bar"),
        ("other", "//foo/bar:spam", "foo/bar", "spam"),
    ],
)
def test_Address_from_address__parse_relative_address(base, address, expected_base, expected_name):
    addr = Address.from_string(base, address)

    compare(addr, Address(base=expected_base, name=expected_name))


@pytest.mark.parametrize(
    ["base", "address"],
    [
        ("treb", "foo"),
        ("treb", "::foo"),
        ("treb", "/foo/bar"),
        ("treb", ":bar:spam"),
    ],
)
def test_Address_from_address__raise_ValueError_if_address_is_invalid(base, address):

    with ShouldRaise(ValueError):
        Address.from_string(base, address)
