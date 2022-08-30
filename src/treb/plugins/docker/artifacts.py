"""Implementation artifacts used to represt Docker images."""
from attrs import define

from treb.core.artifact import Artifact, ArtifactSpec


@define(frozen=True, kw_only=True)
class DockerImageSpec(ArtifactSpec):
    """An artifact spec used to reference a Docker image on a repository.

    Arguments:
        image_name: the name of the image without the tag.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "docker_image"

    image_name: str
    tag_prefix: str = ""


@define(frozen=True, kw_only=True)
class DockerImageArtifact(Artifact):
    """An artifact represetning a tagged and existing Docker iamge."""

    tag: str
