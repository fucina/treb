"""All the steps provided by the docker system."""
from typing import Mapping, Optional

import boto3
from attrs import define

from treb.core.context import Context
from treb.core.step import Step
from treb.plugins.aws.ecs.artifacts import EcsTaskDefinition
from treb.plugins.aws.ecs.resources import EcsService
from treb.plugins.docker.artifacts import DockerImage

ECS_CLIENT = boto3.client("ecs")


@define(frozen=True, kw_only=True)
class RegisterTaskDefinition(Step):
    """Register a new revision for the given task defintion.

    This step overrides only the containers specified in `container`
    updating their image. Any other container will be carried to
    the new revision unchanged.

    All the parameters not managed by this step, such as volumes or
    placement constraints are copied from the latest active revision.

    Arguments:
        task_defintion: the ECS task definition to update.
        containers: a map of all the docker image to update when running
        this step. The key is a string that must match the container name
        inf the task defintion.

    Returns:
        The revision of the new ECS task defintion.
    """

    task_definition: EcsTaskDefinition
    containers: Mapping[str, DockerImage]

    @classmethod
    def spec_name(cls) -> str:
        return "aws_ecs_create_task_revision"

    def snapshot(self, ctx: "Context") -> None:
        return None

    def run(self, ctx: Context, snapshot: None) -> EcsTaskDefinition:
        res = ECS_CLIENT.describe_task_definition(
            taskDefinition=f"{self.task_definition.spec.family}:{self.task_definition.revision}"
        )
        task_defintion = res["taskDefinition"]

        for container in task_defintion["containerDefinitions"]:
            docker_image = self.containers.get(container["name"])
            if docker_image is None:
                continue

            container["image"] = docker_image.tag

        res = ECS_CLIENT.register_task_definition(**task_defintion)
        task_defintion = res["taskDefinition"]

        return EcsTaskDefinition(
            spec=self.task_definition.spec,
            revision=task_defintion["revision"],
        )

    def rollback(self, ctx: Context, snapshot: None):
        pass


@define(frozen=True, kw_only=True)
class EcsServiceSnapshot:
    """A snapshot taken for an ECS service.

    Arguments:
        family: the task definition's family.
        revision: the task defintion's revision number.
    """

    family: str
    revision: int


@define(frozen=True, kw_only=True)
class UpdateEcsService(Step):
    """Update a AWS ECS service with the latest taask revision.

    Arguments:
    """

    ecs_service: EcsService
    task_definition: EcsTaskDefinition

    @classmethod
    def spec_name(cls) -> str:
        return "aws_ecs_update"

    def snapshot(self, ctx: "Context") -> Optional[EcsServiceSnapshot]:
        return EcsServiceSnapshot(
            family=self.ecs_service.task_definition_family,
            revision=self.ecs_service.task_definition_revision,
        )

    def run(self, ctx: Context, snapshot: Optional[EcsServiceSnapshot]) -> EcsService:
        ECS_CLIENT.update_service(
            cluster=self.ecs_service.spec.cluster,
            service=self.ecs_service.spec.name,
            taskDefinition=f"{self.task_definition.spec.family}:{self.task_definition.revision}",
        )

        return EcsService(
            spec=self.ecs_service,
            task_definition_family=self.task_definition.spec.family,
            task_definition_revision=self.task_definition.revision,
        )

    def rollback(self, ctx: Context, snapshot: Optional[EcsServiceSnapshot]):
        if snapshot is None:
            raise Exception("snapshot unavailable")

        ECS_CLIENT.update_service(
            cluster=self.ecs_service.spec.cluster,
            service=self.ecs_service.spec.name,
            taskDefinition=f"{self.task_definition.spec.family}:{self.task_definition.revision}",
        )
