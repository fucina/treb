"""Implementation artifacts used to represt Docker images."""
from typing import Optional

import docker
from attrs import define

from treb.core.artifact import Artifact
from treb.core.context import Context
from treb.plugins.docker.utils import full_tag
from treb.utils import log, print_waiting

CLIENT = docker.from_env()


@define(frozen=True, kw_only=True)
class DockerImage:
    """An artifact representing a tagged and existing Docker iamge."""

    tag: str


@define(frozen=True, kw_only=True)
class DockerImageSpec(Artifact):
    """An artifact spec used to reference a Docker image on a repository.

    Arguments:
        image_name: the name of the image without the tag.
    """

    image_name: str
    tag_prefix: str = ""

    @classmethod
    def spec_name(cls) -> str:
        return "docker_image"

    def exists(self, ctx: Context) -> bool:
        tag = full_tag(self.image_name, self.tag_prefix, ctx.revision)

        with print_waiting("checking registry data"):
            try:
                CLIENT.images.get_registry_data(tag)

            except docker.errors.NotFound:
                return False

        return True

    def resolve(self, ctx: Context) -> Optional[DockerImage]:
        tag = full_tag(self.image_name, self.tag_prefix, ctx.revision)

        with print_waiting("pulling docker image"):
            CLIENT.images.pull(tag)
            log(f"pulled docker image {tag}")

        return DockerImage(tag=tag)
