"""Implementation of an artifact represting a Docker image."""
from attrs import define

from treb.core.artifact import Artifact, ArtifactSpec


@define(frozen=True, kw_only=True)
class DockerImageSpec(ArtifactSpec):

    image_name: str


@define(frozen=True, kw_only=True)
class DockerImageArtifact(Artifact):

    tag: str
