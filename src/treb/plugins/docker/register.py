"""Register the Docker plugin."""
from typing import Sequence, Type

from treb.core.artifact import Artifact
from treb.core.step import Step
from treb.plugins.docker.artifacts import DockerImageSpec
from treb.plugins.docker.steps import DockerPush


def namespace() -> str:
    """Returns the namespace for the Docker plugin."""
    return "docker"


def artifacts() -> Sequence[Type[Artifact]]:
    """Returns all Docker artifacts."""
    return [DockerImageSpec]


def steps() -> Sequence[Type[Step]]:
    """Returns all Docker steps."""
    return [DockerPush]
