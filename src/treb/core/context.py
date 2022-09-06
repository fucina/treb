"""Definiton of the context capturing all the data needed to run treb."""
from typing import Dict

from attrs import define

from treb.core.config import Config
from treb.core.plugin import load_plugin
from treb.core.spec import Spec


@define(frozen=True, kw_only=True)
class Context:
    """Contains all the data needed to run any treb command.

    Arguments:
        config: treb's configuration.
        revision: the SHA-256 commit used to build the artifacts to deploy.
        specs: all the registered step and artifact specs.
    """

    config: Config
    revision: str
    specs: Dict[str, Spec]


def load_context(config: Config, revision: str) -> Context:
    """Prepares the context to be used in treb.

    Arguments:
        config: treb's configuration.

    Retruns:
        The context.
    """
    specs = {}

    for plugin_path in config.plugins:
        plugin = load_plugin(plugin_path)

        for spec in plugin.specs():
            name = spec.spec_name()
            if name in specs:
                raise ValueError(f"spec with name {name} is already present")

            specs[name] = spec

    return Context(
        config=config,
        specs=specs,
        revision=revision,
    )
