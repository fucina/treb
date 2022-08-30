"""Main entrypoint for the `treb` command."""
import os
from typing import Optional

import click

from treb.core.config import load_config
from treb.core.context import Context, load_context
from treb.core.git import get_current_commit
from treb.core.state import init_revision, init_state, load_revision, save_revision
from treb.core.strategy import prepare_strategy
from treb.utils import print_info, print_waiting


@click.group()
@click.option("-c", "--config", "config_path", default="./treb.toml")
@click.option("-r", "--revision", default=None)
@click.option("--cwd", default=None)
@click.pass_context
def cli(ctx: click.Context, config_path: str, revision: Optional[str], cwd: Optional[str]):
    """Entrypoint for the treb command."""
    config = load_config(path=config_path)
    revision = revision or get_current_commit(path=config.project.repo_path)

    ctx.obj = load_context(config=config, revision=revision)

    if cwd is not None:
        os.chdir(cwd)


@cli.command()
@click.pass_obj
def apply(ctx: Context):
    """Execute a deploy plan."""
    init_state(ctx=ctx)
    strategy = prepare_strategy(ctx=ctx)

    init_revision(ctx=ctx)
    revision = load_revision(ctx=ctx)
    strategy_plan = strategy.plan() if revision is None else revision.plan

    with print_waiting("executing plan"):
        for curr_plan in strategy.execute(strategy_plan):  # pylint: disable=not-an-iterable
            save_revision(ctx=ctx, plan=curr_plan)


@cli.command()
@click.pass_obj
def plan(ctx: Context):
    """Shows the plan for a deploy strategy without executing it."""
    strategy = prepare_strategy(ctx=ctx)

    revision = load_revision(ctx=ctx)
    strategy_plan = strategy.plan() if revision is None else revision.plan

    print_info(f"plan: {strategy_plan}")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
