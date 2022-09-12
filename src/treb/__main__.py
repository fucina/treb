"""Main entrypoint for the `treb` command."""
import os
from typing import Optional

import click

from treb.core.config import load_config
from treb.core.context import Context, load_context
from treb.core.execute import execute_plan
from treb.core.git import get_current_commit
from treb.core.plan import generate_plan
from treb.core.state import init_revision, init_state, load_revision, save_revision
from treb.core.strategy import prepare_strategy
from treb.utils import log, print_info, print_waiting


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
@click.option("-f", "--force", is_flag=True, default=False)
@click.pass_obj
def apply(ctx: Context, force: bool):
    """Execute a deploy plan."""
    log("initializing project state")
    init_state(ctx=ctx)

    log("preparing strategy")
    strategy = prepare_strategy(ctx=ctx)

    log("initializing revision state")
    init_revision(ctx=ctx)

    log("loading revision state")
    revision = load_revision(ctx=ctx)

    if revision is None or force:
        available_artifacts = [
            addr for addr, art in strategy.artifacts().items() if art.exists(ctx.revision)
        ]
        strategy_plan = generate_plan(strategy, available_artifacts)

    else:
        strategy_plan = revision.plan

    with print_waiting("executing plan"):
        for curr_plan in execute_plan(strategy, strategy_plan):  # pylint: disable=not-an-iterable
            save_revision(ctx=ctx, plan=curr_plan)


@cli.command()
@click.option("-a", "--all", "all_artifacts", default=False)
@click.pass_obj
def plan(ctx: Context, all_artifacts: bool):
    """Shows the plan for a deploy strategy without executing it."""
    strategy = prepare_strategy(ctx=ctx)

    revision = load_revision(ctx=ctx)

    if revision is None:
        if all_artifacts:
            available_artifacts = list(strategy.artifacts().keys())
        else:
            available_artifacts = [
                addr for addr, art in strategy.artifacts().items() if art.exists(ctx.revision)
            ]

        strategy_plan = generate_plan(strategy, available_artifacts)

    else:
        strategy_plan = revision.plan

    print_info(f"plan: {strategy_plan}")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
