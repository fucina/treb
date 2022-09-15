"""Helpers used to add step and artifact specs to treb."""
from importlib import import_module
from typing import List, cast

from attrs import define

from treb.core.artifact import Artifact
from treb.core.check import Check
from treb.core.resource import Resource
from treb.core.spec import Spec
from treb.core.step import Step


@define(frozen=True, kw_only=True)
class Plugin:
    """A treb plugin that provides step and artifact specs."""

    namespace: str
    steps: List[Step]
    artifacts: List[Artifact]
    resources: List[Resource]
    checks: List[Check]

    def specs(self) -> List[Spec]:
        """Gets all the spec defined in this plug-in."""
        artifacts: List[Spec] = cast(List[Spec], self.artifacts)
        checks: List[Spec] = cast(List[Spec], self.checks)
        resources: List[Spec] = cast(List[Spec], self.resources)
        steps: List[Spec] = cast(List[Spec], self.steps)

        return artifacts + checks + resources + steps


def load_plugin(module: str) -> Plugin:
    """Loads a plugin that exposes step and artifact specs in a submodule
    `register`.

    Arguments:
        module: import path of the plugin.
    """
    register = import_module(f"{module}.register")

    steps: List[Step] = cast(List[Step], getattr(register, "steps", lambda: [])())
    artifacts: List[Artifact] = cast(List[Artifact], getattr(register, "artifacts", lambda: [])())
    checks: List[Check] = cast(List[Check], getattr(register, "checks", lambda: [])())
    resources: List[Resource] = cast(List[Resource], getattr(register, "resources", lambda: [])())

    return Plugin(
        namespace=register.namespace(),
        artifacts=artifacts,
        checks=checks,
        resources=resources,
        steps=steps,
    )
