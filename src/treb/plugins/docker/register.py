"""Register the Docker plugin."""
from typing import List

from treb.core.artifact import ArtifactSpec
from treb.core.step import Step
from treb.plugins.docker.artifacts import DockerImageSpec
from treb.plugins.docker.steps import DockerPull, DockerPush


def namespace() -> str:
    """Returns the namespace for the Dcoker plugin."""
    return "docker"


def artifacts() -> List[ArtifactSpec]:
    """Returns all Docker artifacts."""
    return [DockerImageSpec]


def steps() -> List[Step]:
    """Returns all Docker steps."""
    return [DockerPush, DockerPull]
