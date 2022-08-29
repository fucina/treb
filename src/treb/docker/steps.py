"""All the steps provided by the docker system."""
import docker
from attrs import define

from treb.core.context import Context
from treb.core.step import Step
from treb.docker.artifact import DockerImageArtifact, DockerImageSpec

CLIENT = docker.from_env()


@define(frozen=True, kw_only=True)
class DockerPull(Step):
    """Pulls a docker image from a remote registry.

    Arguments:
        origin: spec of the image to pull.
    """

    origin: DockerImageSpec

    def run(self, ctx: Context) -> DockerImageArtifact:
        tag = f"{self.origin.image_name}:{ctx.revision}"
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

    origin: DockerImageArtifact
    dest: DockerImageSpec

    def run(self, ctx: Context) -> DockerImageArtifact:
        dest_tag = f"{self.dest.image_name}:{ctx.revision}"

        image = CLIENT.images.get(self.origin.tag)
        image.tag(dest_tag)
        CLIENT.images.push(dest_tag)

        return DockerImageArtifact(tag=dest_tag)

    def rollback(self, ctx):
        pass
