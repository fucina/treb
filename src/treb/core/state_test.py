import os
from pathlib import Path
from unittest import mock

import pytest
from attrs import evolve
from testfixtures import compare

from treb.core.config import Config, ProjectConfig, StateConfig
from treb.core.context import Context
from treb.core.plan import Plan
from treb.core.state import (
    Revision,
    get_base_path,
    get_revision_path,
    get_revisions_path,
    init_revision,
    init_state,
    load_revision,
    save_revision,
)


@pytest.fixture
def treb_context(tmp_path_factory) -> Context:
    state_path = tmp_path_factory.mktemp("state")
    proj_path = tmp_path_factory.mktemp("proj")

    config = Config(
        state=StateConfig(repo_path=str(state_path)),
        project=ProjectConfig(repo_path=str(proj_path)),
    )

    ctx = Context(
        config=config,
        revision="abc",
    )

    return ctx


def test_get_base_path__generate_base_path_from_root(treb_context):
    res = get_base_path(treb_context)

    compare(res, Path(treb_context.config.state.repo_path))


def test_get_base_path__generate_base_path_from_nested_path(treb_context):
    treb_context = evolve(
        treb_context,
        config=evolve(
            treb_context.config,
            state=evolve(
                treb_context.config.state,
                base_path="foo",
            ),
        ),
    )

    res = get_base_path(treb_context)

    compare(res, Path(treb_context.config.state.repo_path) / "foo")


def test_get_revisions_path__generate_revisions_path(treb_context):

    res = get_revisions_path(treb_context)

    compare(res, Path(treb_context.config.state.repo_path) / "revisions")


def test_get_revision_path__generate_revision_path(treb_context):
    res = get_revision_path(treb_context)

    compare(res, Path(treb_context.config.state.repo_path) / "revisions" / "abc")


def test_init_state__create_missing_directories(treb_context):
    init_state(treb_context)

    state_path = Path(treb_context.config.state.repo_path)

    res = sorted(Path(dirpath) for dirpath, _, _ in os.walk(state_path))

    compare(
        res,
        [
            state_path,
            state_path / "revisions",
        ],
    )


def test_init_revision__create_missing_directories(treb_context):
    init_state(treb_context)
    init_revision(treb_context)

    state_path = Path(treb_context.config.state.repo_path)

    res = sorted(Path(dirpath) for dirpath, _, _ in os.walk(state_path))

    compare(
        res,
        [
            state_path,
            state_path / "revisions",
            state_path / "revisions" / "abc",
        ],
    )


@mock.patch("treb.core.state.git")
def test_save_revision__persist_revision_state(git, treb_context):
    plan = Plan(actions=[])

    init_state(treb_context)
    init_revision(treb_context)

    save_revision(treb_context, plan)

    rev_state_path = Path(treb_context.config.state.repo_path) / "revisions" / "abc" / "state.json"

    compare(rev_state_path.exists(), True)
    compare(rev_state_path.is_file(), True)

    git.commit.assert_called_once()
    git.push.assert_called_once()

    rev = load_revision(treb_context)

    compare(rev, Revision(plan=plan))


@mock.patch("treb.core.state.git")
def test_save_revision__do_not_push(git, treb_context):
    treb_context = evolve(
        treb_context,
        config=evolve(
            treb_context.config,
            state=evolve(
                treb_context.config.state,
                push=False,
            ),
        ),
    )
    plan = Plan(actions=[])

    init_state(treb_context)
    init_revision(treb_context)

    save_revision(treb_context, plan)

    git.commit.assert_called_once()
    git.push.assert_not_called()


def test_load_revision__return_none_if_revision_state_does_not_exist(treb_context):
    init_state(treb_context)

    res = load_revision(treb_context)

    compare(res, None)
