"""Implementation artifacts used to represent ECS task defintions."""
from typing import Optional

import boto3
from attrs import define

from treb.core.artifact import Artifact
from treb.core.context import Context

ECS_CLIENT = boto3.client("ecs")

REVISION_TAG_PREFIX = "treb_revision_"


@define(frozen=True, kw_only=True)
class EcsTaskDefinition:
    """An artifact representing an existing ECS task definition.

    Arguments:
        spec: the artifact spec that defined this task defition.
        revision: the task defintion's revision number.
    """

    spec: "EcsTaskDefinitionSpec"

    revision: int


@define(frozen=True, kw_only=True)
class EcsTaskDefinitionSpec(Artifact):
    """An artifact spec used to reference an ECS task definition.

    Arguments:
        family: the task definition's family.
    """

    family: str

    @classmethod
    def spec_name(cls) -> str:
        return "aws_ecs_task_definition"

    def resolve(self, ctx: Context) -> Optional[EcsTaskDefinition]:
        paginator = ECS_CLIENT.get_paginator("list_task_definitions")

        for task_defintion_arn in paginator.paginate(
            familyPrefix=self.family,
            status="ACTIVE",
            sort="DESC",
        ):
            family, _, revision = task_defintion_arn.rpartition("/")[2].partition(":")

            if family != self.family:
                continue

            res = ECS_CLIENT.describe_task_definition(
                taskDefinition=f"{family}:{revision}", include=["TAGS"]
            )
            task_defintion = res["taskDefinition"]

            for tag in task_defintion["tags"]:
                if not tag["key"].starts_with(REVISION_TAG_PREFIX):
                    continue

                if tag["key"] == ctx.revision:
                    return EcsTaskDefinition(spec=self, revision=int(revision))

        return None
