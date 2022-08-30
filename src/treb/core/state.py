"""Manages the state persisted in Git."""

import json
from pathlib import Path
from typing import Optional

from attrs import define
from cattrs import structure, unstructure

from treb.core import git
from treb.core.context import Context
from treb.core.plan import Plan


def get_base(ctx: Context) -> Path:
    """Gets the path to the state repository.

    Arguments:
        ctx: treb's context containing the state configuration.

    Returns:
        Path to the state repository.
    """
    if ctx.config.state.base_path is None:
        return Path(ctx.config.state.repo_path)

    return Path(ctx.config.state.repo_path).joinpath(ctx.config.state.base_path)


def get_revisions(ctx: Context) -> Path:
    """Gets the path to the directory containing all the revisions.

    Arguments:
        ctx: treb's context containing the state configuration.

    Returns:
        Path to the revisions directory.
    """
    base_path = get_base(ctx)

    return base_path.joinpath("revisions")


def get_revision(ctx: Context) -> Path:
    """Gets the path to the directory containing the data of a specific
    revision.

    Arguments:
        ctx: treb's context containing the state configuration.

    Returns:
        Path to a revision directory.
    """
    rev_path = get_revisions(ctx)

    return rev_path.joinpath(ctx.revision)


def init_state(ctx: Context):
    """Initializes a Git repository and prepare it to be used as state storage.

    Arguments:
        ctx: treb's context containing the state configuration.
    """
    base_path = get_base(ctx)
    base_path.mkdir(parents=True, exist_ok=True)

    rev_path = get_revisions(ctx)
    rev_path.mkdir(parents=True, exist_ok=True)


def init_revision(ctx: Context):
    """Initializes the subdirectory in the state repository that contains the
    state for every single revision deployed by treb.

    Arguments:
        ctx: treb's context containing the state configuration.
    """
    rev_path = get_revision(ctx)
    rev_path.mkdir(parents=True, exist_ok=True)


@define(frozen=True, kw_only=True)
class Revision:
    """Contains all the information about the current state of a deployment
    from a specific revision.

    Arguments:
        plan: the current state of the plan.
    """

    plan: Plan


def save_revision(ctx: Context, plan: Plan):
    """Update the plan state and persists it.

    Arguments:
        path: path of the file where the plan will be stored.
        plan: plan to store.
    """
    rev_path = get_revision(ctx)
    state_path = rev_path.joinpath("state.json")

    revision = Revision(plan=plan)

    with open(state_path, "w", encoding="utf-8") as plan_file:
        encoded = unstructure(revision)
        plan_file.write(json.dumps(encoded, indent=4, sort_keys=True))

    git.commit(path=ctx.config.state.repo_path, message=f"update state for revision {ctx.revision}")

    if ctx.config.state.push:
        git.push(path=ctx.config.state.repo_path, remote_location=ctx.config.state.remote_location)


def load_revision(ctx: Context) -> Optional[Revision]:
    """Loads the current revision state from a file.

    Arguments:
        ctx: treb's context containing the state configuration.

    Returns:
        The revision state if present. Otherwise, returns `None`.
    """
    rev_path = get_revision(ctx)
    state_path = rev_path.joinpath("state.json")

    try:
        with open(state_path, encoding="utf-8") as plan_file:
            decoded = json.loads(plan_file.read())

            return structure(decoded, Revision)

    except FileNotFoundError:
        return None
