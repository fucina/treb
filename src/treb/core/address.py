import abc

from attrs import define


@define(frozen=True, kw_only=True)
class Address:

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
    def from_string(cls, frombase: str, addr: str) -> "Address":
        if addr.startswith(":"):
            base = frombase
            name = addr[1:]

        elif addr.startswith("//"):
            base, _, name = addr[2:].rpartion(":")

        else:
            raise ValueError("invalid address format")

        return cls(
            base=base,
            name=name,
        )
