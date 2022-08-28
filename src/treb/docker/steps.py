import docker
from attrs import define

from treb.core.address import Address
from treb.core.context import Context
from treb.core.step import Step
from treb.docker.artifact import DockerImageArtifact, DockerImageSpec

CLIENT = docker.from_env()


@define(frozen=True, kw_only=True)
class DockerPull(Step):

    origin: DockerImageSpec

    def run(self, ctx: Context) -> DockerImageArtifact:
        tag = f"{self.origin.image_name}:{ctx.revision}"
        CLIENT.images.pull(tag)

        return DockerImageArtifact(tag=tag)

    def rollback(self, ctx):
        pass


@define(frozen=True, kw_only=True)
class DockerPush(Step):

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
