"""Base class for all the specs used to define a deploy strategy."""
import abc
from typing import List

from attrs import define, field


@define(frozen=True, kw_only=True)
class Spec(abc.ABC):
    """Base class to be used for all steps.

    Arguments:
        name: identify a step within a deploy file.
        after: perform this spec only after all the specs in the list
            have been executed.
    """

    name: str
    after: List[str] = field(factory=list)

    @classmethod
    @abc.abstractmethod
    def spec_name(cls) -> str:
        """Returns the name of this type of artifacts."""
        raise NotImplementedError
