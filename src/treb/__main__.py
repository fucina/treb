"""Main entrypoint for the `treb` command."""
import os
from typing import Optional

import click

from treb.core.config import load_config
from treb.core.context import Context, load_context
from treb.core.git import get_current_commit
from treb.core.plan import dump_plan, load_plan
from treb.core.strategy import prepare_strategy
from treb.utils import print_info, print_waiting


@click.group()
@click.option("-c", "--config", "config_path", default="./treb.toml")
@click.option("-r", "--revision", default=None)
@click.pass_context
def cli(ctx: click.Context, config_path: str, revision: Optional[str]):
    """Entrypoint for the treb command."""
    config = load_config(path=config_path)
    revision = revision or get_current_commit(path=config.project.repo_path)

    ctx.obj = load_context(config=config, revision=revision)


@cli.command()
@click.option("-p", "--plan", "plan_path", default=None)
@click.pass_obj
def apply(ctx: Context, plan_path: Optional[str]):
    """Execute a deploy plan."""
    strategy = prepare_strategy(ctx=ctx)

    if plan_path:
        strategy_plan = load_plan(plan_path)

    else:
        strategy_plan = strategy.plan()

    with print_waiting("executing plan"):
        for curr_plan in strategy.execute(strategy_plan):  # pylint: disable=not-an-iterable
            dump_plan(os.path.join(ctx.config.state.repo_path, "plan", ctx.revision), curr_plan)


@cli.command()
@click.option("-p", "--plan", "plan_path", default=None)
@click.pass_obj
def plan(ctx: Context, plan_path: Optional[str]):
    """Shows the plan for a deploy strategy without executing it."""
    strategy = prepare_strategy(ctx=ctx)

    if plan_path:
        strategy_plan = load_plan(plan_path)

    else:
        strategy_plan = strategy.plan()

    print_info(f"plan: {strategy_plan}")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
