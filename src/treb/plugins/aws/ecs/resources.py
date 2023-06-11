"""Implementation of the resources used to represent AWS ECS services."""
from typing import Optional

import boto3
from attrs import define

from treb.core.context import Context
from treb.core.resource import Resource

ECS_CLIENT = boto3.client("ecs")


@define(frozen=True, kw_only=True)
class EcsService:
    """A resource representing an ECS Service on AWS.

    Arguments:
        spec: the ECS service spec associated to this resource.
        task_definition_family: the family of the task defition
        used by this service.
        task_definition_revision: the revision of the task defition
        used by this service.
    """

    spec: "EcsServiceSpec"

    task_definition_family: str
    task_definition_revision: str


@define(frozen=True, kw_only=True)
class EcsServiceSpec(Resource):
    """A resource spec used to reference a Cloud Run Service on GCP.

    Arguments:
        image_name: the name of the image without the tag.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "aws_ecs_service"

    cluster: str
    service_name: str

    def state(self, ctx: Context) -> Optional[EcsService]:
        res = ECS_CLIENT.describe_services(
            cluster=self.cluster,
            services=[self.service_name],
        )

        if not res["services"]:
            return None

        service = res["services"][0]

        task_defintion_arn = service["taskDefinition"]
        family, _, revision = task_defintion_arn.rpartition("/")[2].partition(":")

        return EcsService(
            spec=self,
            task_definition_family=family,
            task_definition_revision=revision,
        )
