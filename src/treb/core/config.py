from typing import Dict

import toml
from attrs import define, field
from cattrs import structure


@define(frozen=True, kw_only=True)
class StateConfig:

    repo_path: str


@define(frozen=True, kw_only=True)
class ProjectConfig:

    repo_path: str


@define(frozen=True, kw_only=True)
class Config:

    state: StateConfig
    deploy_filename: str = "DEPLOY"
    projects: Dict[str, ProjectConfig] = field(factory=list)


def load_config(path: str) -> Config:
    config = toml.load(path)

    return structure(config, Config)
