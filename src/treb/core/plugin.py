"""Helpers used to add step and artifact specs to treb."""
from importlib import import_module
from typing import List, Sequence

from attrs import define

from treb.core.artifact import ArtifactSpec
from treb.core.check import Check
from treb.core.spec import Spec
from treb.core.step import Step


@define(frozen=True, kw_only=True)
class Plugin:
    """A treb plugin that provides step and artifact specs."""

    namespace: str
    steps: List[Step]
    artifacts: List[ArtifactSpec]
    checks: List[Check]

    def specs(self) -> Sequence[Spec]:
        return self.steps + self.artifacts + self.checks


def load_plugin(module: str) -> Plugin:
    """Loads a plugin that exposes step and artifact specs in a submodule
    `register`.

    Arguments:
        module: import path of the plugin.
    """
    register = import_module(f"{module}.register")

    steps = getattr(register, "steps", lambda: [])()
    artifacts = getattr(register, "artifacts", lambda: [])()
    checks = getattr(register, "checks", lambda: [])()

    return Plugin(
        namespace=register.namespace(),
        steps=steps,
        artifacts=artifacts,
        checks=checks,
    )
