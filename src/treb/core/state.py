from typing import Dict

from attrs import define

from treb.core.artifact import ArtifactSpec
from treb.core.context import Context


@define(frozen=True, kw_only=True)
class State:
    pass


def load_state(ctx: Context) -> State:
    from treb.docker.artifact import DockerImageSpec

    return State()
