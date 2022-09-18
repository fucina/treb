"""All the steps provided by the docker system."""
import docker
from attrs import define

from treb.core.context import Context
from treb.core.step import Step
from treb.plugins.docker.artifacts import DockerImage, DockerImageSpec
from treb.plugins.docker.utils import full_tag
from treb.utils import log, print_waiting

CLIENT = docker.from_env()


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

    origin: DockerImage

    dest_image_name: str
    dest_tag_prefix: str = ""

    def run(self, ctx: Context) -> DockerImage:
        if self.origin is None:
            raise Exception(f"image for revision {ctx.revision} does not exist")

        dest_tag = full_tag(self.dest_image_name, self.dest_tag_prefix, ctx.revision)

        image = CLIENT.images.get(self.origin.tag)
        image.tag(dest_tag)

        with print_waiting("pushing docker image"):
            CLIENT.images.push(dest_tag)
            log(f"pushed docker image from {self.origin.tag} to {dest_tag}")

        return DockerImage(
            spec=DockerImageSpec(
                name="",
                image_name=self.dest_image_name,
                tag_prefix=self.dest_tag_prefix,
            ),
            tag=dest_tag,
        )

    def rollback(self, ctx: Context):
        pass
