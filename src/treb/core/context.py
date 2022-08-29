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


def load_context(config: Config, revision: str) -> Context:
    """Prepares the context to be used in treb.

    Arguments:
        config: treb's configuration.

    Retruns:
        The context.
    """
    return Context(
        config=config,
        artifact_specs={},
        revision=revision,
    )
