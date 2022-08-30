"""All the steps provided by the docker system."""
import docker
from attrs import define

from treb.core.context import Context
from treb.core.step import Step
from treb.plugins.docker.artifacts import DockerImageArtifact, DockerImageSpec
from treb.utils import print_waiting

CLIENT = docker.from_env()


@define(frozen=True, kw_only=True)
class DockerPull(Step):
    """Pulls a docker image from a remote registry.

    Arguments:
        origin: spec of the image to pull.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "docker_pull"

    origin: DockerImageSpec

    def run(self, ctx: Context) -> DockerImageArtifact:
        tag = f"{self.origin.image_name}:{self.origin.tag_prefix}{ctx.revision}"

        with print_waiting("pulling docker image"):
            CLIENT.images.pull(tag)

        return DockerImageArtifact(tag=tag)

    def rollback(self, ctx):
        pass


@define(frozen=True, kw_only=True)
class DockerPush(Step):
    """Re-tag a local image and push it to a remote registry.

    Arguments:
        origin: the local image to push.
        dest: spec of the image to push.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "docker_push"

    origin: DockerImageArtifact
    dest: DockerImageSpec

    def run(self, ctx: Context) -> DockerImageArtifact:
        dest_tag = f"{self.dest.image_name}:{self.dest.tag_prefix}{ctx.revision}"

        image = CLIENT.images.get(self.origin.tag)
        image.tag(dest_tag)

        with print_waiting("pushing docker image"):
            CLIENT.images.push(dest_tag)

        return DockerImageArtifact(tag=dest_tag)

    def rollback(self, ctx):
        pass
