"""Representation of an address for any artifact or step."""
from typing import Optional

from attrs import define, field

__all__ = ["Address", "is_valid_name"]


def is_valid_name(name: str) -> bool:
    """Checks if the name used in an address is valid.

    Valid name MUST match the following requirements:

    * have at least one character
    * first character is alphabetic [a-zA-Z]
    * last character cannot be `-`
    * any other character can be alphanumeric or `-`
    """
    if len(name) == 0:
        return False

    if not name[0].isalpha():
        return False

    if name[-1] == "-":
        return False

    return all((ch.isalnum() or ch == "-") for ch in name)


@define(frozen=True, kw_only=True, order=True)
class Address:
    """Represent an address used to identify a step or artifact in a deploy
    strategy.

    Arguments:
        base: path to the directory of the deploy file where this spec is defined.
        name: identifies a spec within a single deploy file.
        attr: points to a attribute in the spec result. Same syntax as `operator.attrgetter`.
    """

    base: str
    name: str = field()
    attr: Optional[str] = field(default=None)

    @name.validator
    def check_name(self, _, value):  # pylint: disable=no-self-use
        """Validates the address' name."""
        if not is_valid_name(value):
            raise ValueError(f"invalid address name {value}")

    def __str__(self):
        return f"//{self.base}:{self.name}"

    def __repr__(self):
        return f"Address({self.base!r}, {self.name!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Address):
            return self.base == other.base and self.name == other.name

        return False

    def __hash__(self) -> int:
        return hash(str(self))

    @classmethod
    def from_string(cls, base: str, addr: str) -> "Address":
        """Creates an instance of Address from its string representation.

        The address can be either relative (i.e. `:image`, `pull-image`) or
        absolute (i.e. `//foo:image`, `//bar/spam:pull-image`).

        When an absolute address is passed, it will ignore the give base path.

        Arguments:
            base: the base directory to use if the address is relative i.e. `:image`.
            addr: the address to convert.

        Returns:
            The address represented by the given string.

        Raises:
            ValueError: if the address is invalid.
        """
        if addr.startswith(":"):
            postfix = addr[1:]

        elif addr.startswith("//"):
            base, _, postfix = addr[2:].rpartition(":")

        else:
            raise ValueError(f"invalid address format {addr}")

        name, _, attr = postfix.partition("#")

        return Address(
            base=base,
            name=name,
            attr=attr if attr else None,
        )

    @property
    def without_attr(self) -> "Address":
        """Returns the address without the attr part."""
        return Address(
            base=self.base,
            name=self.name,
        )
