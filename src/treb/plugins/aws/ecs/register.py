"""Register the AWS ECS plugin."""
from typing import Sequence, Type

from treb.core.artifact import Artifact
from treb.core.step import Step
from treb.plugins.aws.ecs.artifacts import EcsTaskDefinition
from treb.plugins.aws.ecs.resources import EcsService
from treb.plugins.aws.ecs.steps import RegisterTaskDefinition, UpdateEcsService


def namespace() -> str:
    """Returns the namespace for the AWS ECS plugin."""
    return "cloudflare"


def artifacts() -> Sequence[Type[Artifact]]:
    """Returns all AWS ECS artifacts."""
    return [EcsService, EcsTaskDefinition]


def steps() -> Sequence[Type[Step]]:
    """Returns all AWS ECS steps."""
    return [UpdateEcsService, RegisterTaskDefinition]
