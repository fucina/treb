"""Main entrypoint for the `treb` command."""
import os

import click

from treb.core.config import load_config
from treb.core.context import load_context
from treb.core.plan import dump_plan, load_plan
from treb.core.strategy import prepare_strategy
from treb.utils import print_info, print_waiting


@click.group()
def cli():
    """Entrypoint for the treb command."""


@cli.command()
@click.option("-c", "--config", "config_path", default="./treb.toml")
@click.option("-p", "--plan", "plan_path", default=None)
def apply(config_path: str, plan_path: str):
    """Execute a deploy plan."""
    config = load_config(path=config_path)
    ctx = load_context(config=config)
    strategy = prepare_strategy(ctx=ctx)

    if plan_path:
        strategy_plan = load_plan(plan_path)

    else:
        strategy_plan = strategy.plan()

    with print_waiting("executing plan"):
        for curr_plan in strategy.execute(strategy_plan):
            dump_plan(os.path.join(ctx.config.state.repo_path, "plan", ctx.revision), curr_plan)


@cli.command()
@click.option("-c", "--config", "config_path", default="./treb.toml")
@click.option("-p", "--plan", "plan_path", default=None)
def plan(config_path: str, plan_path: str):
    """Shows the plan for a deploy strategy without executing it."""
    config = load_config(path=config_path)
    ctx = load_context(config=config)
    strategy = prepare_strategy(ctx=ctx)

    if plan_path:
        strategy_plan = load_plan(plan_path)

    else:
        strategy_plan = strategy.plan()

    print_info(f"plan: {strategy_plan}")


if __name__ == "__main__":
    cli()
