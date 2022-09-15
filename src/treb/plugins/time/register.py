"""Register the Docker plugin."""
from typing import Sequence, Type

from treb.core.artifact import Artifact
from treb.core.step import Step
from treb.plugins.time.steps import Wait


def namespace() -> str:
    """Returns the namespace for the time plugin."""
    return "time"


def artifacts() -> Sequence[Type[Artifact]]:
    """Returns all time artifacts."""
    return []


def steps() -> Sequence[Type[Step]]:
    """Returns all time steps."""
    return [Wait]
