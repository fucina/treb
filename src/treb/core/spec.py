"""Base class for all the specs used to define a deploy strategy."""
import abc

from attrs import define


@define(frozen=True, kw_only=True)
class Spec(abc.ABC):
    """Base class to be used for all steps.

    Arguments:
        name: identify a step within a deploy file.
    """

    name: str

    @classmethod
    @abc.abstractmethod
    def spec_name(cls) -> str:
        """Returns the name of this type of artifacts."""
        raise NotImplementedError
