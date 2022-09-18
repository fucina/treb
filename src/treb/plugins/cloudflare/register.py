"""Register the Docker plugin."""
from typing import Sequence, Type

from treb.core.artifact import Artifact
from treb.core.step import Step
from treb.plugins.cloudflare.artifacts import PagesDeploymentSpec
from treb.plugins.cloudflare.steps import CloudflareUpdateDns


def namespace() -> str:
    """Returns the namespace for the Cloudflare plugin."""
    return "cloudflare"


def artifacts() -> Sequence[Type[Artifact]]:
    """Returns all Cloudflare artifacts."""
    return [PagesDeploymentSpec]


def steps() -> Sequence[Type[Step]]:
    """Returns all Cloudflare steps."""
    return [CloudflareUpdateDns]
