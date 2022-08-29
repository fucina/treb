"""Definiton of the context capturing all the data needed to run treb."""
from typing import TYPE_CHECKING, Dict

from attrs import define

from treb.core.config import Config

if TYPE_CHECKING:
    from treb.core.artifact import ArtifactSpec


@define(frozen=True, kw_only=True)
class Context:
    """Contains all the data needed to run any treb command.

    Arguments:
        config: treb's configuration.
        revision: the SHA-256 commit used to build the artifacts to deploy.
        artifact_specs: all the registered artifact specs.
    """

    config: Config
    revision: str
    artifact_specs: Dict[str, "ArtifactSpec"]


def load_context(config: Config) -> Context:
    """Prepares the context to be used in treb.

    Arguments:
        config: treb's configuration.

    Retruns:
        The context.
    """
    from treb.docker.artifact import DockerImageSpec
    from treb.docker.steps import DockerPull, DockerPush

    return Context(
        config=config,
        artifact_specs={
            "docker_image": DockerImageSpec,
            "docker_pull": DockerPull,
            "docker_push": DockerPush,
        },
        revision="438a0191f73ea8a77ad2d88b4fc8613a52cec5cc",
    )
