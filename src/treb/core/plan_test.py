from testfixtures import ShouldRaise, compare

from treb.core.address import Address
from treb.core.plan import UnresolvableAddress, resolve_addresses


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
