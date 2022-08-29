"""Register the Docker plugin."""
from typing import Sequence, Type

from treb.core.artifact import ArtifactSpec
from treb.core.step import Step
from treb.plugins.docker.artifacts import DockerImageSpec
from treb.plugins.docker.steps import DockerPull, DockerPush


def namespace() -> str:
    """Returns the namespace for the Dcoker plugin."""
    return "docker"


def artifacts() -> Sequence[Type[ArtifactSpec]]:
    """Returns all Docker artifacts."""
    return [DockerImageSpec]


def steps() -> Sequence[Type[Step]]:
    """Returns all Docker steps."""
    return [DockerPush, DockerPull]
