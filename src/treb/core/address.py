"""Representation of an address for any artifact or step."""
from attrs import define


@define(frozen=True, kw_only=True)
class Address:
    """Represent an address used to identify a step or artifact in a deploy
    strategy.

    Arguments:
        base: base path of the directory where the deploy file is loacated with
            this step/artifact definition.
    """

    base: str
    name: str

    def __str__(self):
        return f"//{self.base}:{self.name}"

    def __repr__(self):
        return f"Address({self.base!r}, {self.name!r})"

    def _validate(self):
        pass

    def __eq__(self, other: "Address") -> bool:
        return self.base == other.base and self.name == other.name

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
            name = addr[1:]

        elif addr.startswith("//"):
            base, _, name = addr[2:].rpartion(":")

        else:
            raise ValueError("invalid address format")

        return cls(
            base=base,
            name=name,
        )
