"""Functions and data structures used to represent and manage treb
configuration."""
from pathlib import Path

import toml
from attrs import define
from cattrs import structure


@define(frozen=True, kw_only=True)
class StateConfig:
    """Configuration for the state storage.

    Arguments:
        repo_path: path to the repository used to store the state.
    """

    repo_path: str


@define(frozen=True, kw_only=True)
class ProjectConfig:
    """Configuration for a project.

    Arguments:
        repo_path: path to the project's repository.
    """

    repo_path: str


@define(frozen=True, kw_only=True)
class Config:
    """treb's configuration.

    Arguments:
        state: confguration for the state storage.
        project: the project tracked by treb.
        deploy_filename: name used to discover the deploy files.
    """

    state: StateConfig
    project: ProjectConfig
    deploy_filename: str = "DEPLOY"


def load_config(path: Path | str) -> Config:
    """Loads the configuration from a file.

    Arguments:
        path: configuration file's path.
    """
    config = toml.load(path)

    return structure(config, Config)
