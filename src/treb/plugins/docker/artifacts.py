"""Implementation artifacts used to represt Docker images."""
import docker
from attrs import define

from treb.core.artifact import Artifact, ArtifactSpec

CLIENT = docker.from_env()


@define(frozen=True, kw_only=True)
class DockerImageSpec(ArtifactSpec):
    """An artifact spec used to reference a Docker image on a repository.

    Arguments:
        image_name: the name of the image without the tag.
    """

    image_name: str
    tag_prefix: str = ""

    @classmethod
    def spec_name(cls) -> str:
        return "docker_image"

    def exists(self, revision: str) -> bool:
        tag = f"{self.image_name}:{self.tag_prefix}{revision}"

        try:
            CLIENT.images.get_registry_data(tag)

        except docker.errors.NotFound:
            return False

        return True


@define(frozen=True, kw_only=True)
class DockerImageArtifact(Artifact):
    """An artifact representing a tagged and existing Docker iamge."""

    tag: str
