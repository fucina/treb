"""Register the Docker plugin."""
from typing import Sequence, Type

from treb.core.resource import Resource
from treb.core.step import Step
from treb.plugins.gcp.cloudrun.resources import CloudRunServiceSpec
from treb.plugins.gcp.cloudrun.steps import CloudRunDeploy


def namespace() -> str:
    """Returns the namespace for the GCP Cloud Run plugin."""
    return "gcp_cloudrun"


def resources() -> Sequence[Type[Resource]]:
    """Returns all GCP Cloud Run artifacts."""
    return [CloudRunServiceSpec]


def steps() -> Sequence[Type[Step]]:
    """Returns all GCP Cloud Run steps."""
    return [CloudRunDeploy]
