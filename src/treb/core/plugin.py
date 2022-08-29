"""Helpers used to add step and artifact specs to treb."""
from importlib import import_module
from typing import List

from attrs import define

from treb.core.artifact import ArtifactSpec
from treb.core.step import Step


@define(frozen=True, kw_only=True)
class Plugin:
    """A treb plugin that provides step and artifact specs."""

    namespace: str
    steps: List[Step]
    artifacts: List[ArtifactSpec]


def load_plugin(module: str):
    """Loads a plugin that exposes step and artifact specs in a submodule
    `register`.

    Arguments:
        module: import path of the plugin.
    """
    register = import_module(f"{module}.register")

    return Plugin(
        namespace=register.namespace(),
        steps=register.steps(),
        artifacts=register.artifacts(),
    )
