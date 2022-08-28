from typing import TYPE_CHECKING, Dict

from attrs import define

from treb.core.config import Config

if TYPE_CHECKING:
    from treb.core.artifact import ArtifactSpec


@define(frozen=True, kw_only=True)
class Context:

    config: Config
    revision: str
    artifact_specs: Dict[str, "ArtifactSpec"]
