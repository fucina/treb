"""Register the Docker plugin."""
from typing import Sequence, Type

from treb.core.artifact import ArtifactSpec
from treb.core.step import Step
from treb.plugins.gcp.cloudrun.artifacts import CloudRunServiceSpec
from treb.plugins.gcp.cloudrun.steps import CloudRunDeploy


def namespace() -> str:
    """Returns the namespace for the GCP Cloud Run plugin."""
    return "gcp_cloudrun"


def artifacts() -> Sequence[Type[ArtifactSpec]]:
    """Returns all GCP Cloud Run artifacts."""
    return [CloudRunServiceSpec]


def steps() -> Sequence[Type[Step]]:
    """Returns all GCP Cloud Run steps."""
    return [CloudRunDeploy]
