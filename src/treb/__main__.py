"""Main entrypoint for the `treb` command."""
import os
from typing import Optional

import click
from rich.table import Table

from treb.core.config import load_config
from treb.core.context import Context, load_context
from treb.core.execute import execute_plan
from treb.core.git import get_current_commit
from treb.core.plan import ActionState, generate_plan
from treb.core.state import init_revision, init_state, load_revision, save_revision
from treb.core.strategy import prepare_strategy
from treb.utils import CONSOLE, log, print_waiting


@click.group()
@click.option("-c", "--config", "config_path", default="./treb.toml")
@click.option("-r", "--revision", default=None)
@click.option("--cwd", default=None)
@click.pass_context
def cli(ctx: click.Context, config_path: str, revision: Optional[str], cwd: Optional[str]):
    """Entrypoint for the treb command."""
    if cwd is not None:
        os.chdir(cwd)

    config = load_config(path=config_path)
    revision = revision or get_current_commit(path=config.project.repo_path)

    ctx.obj = load_context(config=config, revision=revision)


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
            addr for addr, art in strategy.artifacts().items() if art.exists(ctx)
        ]
        strategy_plan = generate_plan(strategy, available_artifacts)

    else:
        strategy_plan = revision.plan

    with print_waiting("executing plan"):
        for curr_plan in execute_plan(strategy, strategy_plan):  # pylint: disable=not-an-iterable
            save_revision(ctx=ctx, plan=curr_plan)


@cli.command()
@click.option("-a", "--all", "all_artifacts", is_flag=True, default=False)
@click.option("-f", "--force", is_flag=True, default=False)
@click.pass_obj
def plan(ctx: Context, all_artifacts: bool, force: bool):
    """Shows the plan for a deploy strategy without executing it."""
    strategy = prepare_strategy(ctx=ctx)

    if force:
        revision = None

    else:
        revision = load_revision(ctx=ctx)

    if revision is None:
        if all_artifacts:
            available_artifacts = list(strategy.artifacts().keys())
        else:
            available_artifacts = [
                addr for addr, art in strategy.artifacts().items() if art.exists(ctx)
            ]

        strategy_plan = generate_plan(strategy, available_artifacts)

    else:
        strategy_plan = revision.plan

    table = Table(title="Plan")
    table.add_column("#", justify="right")
    table.add_column("Type", justify="right")
    table.add_column("Address")
    table.add_column("State", justify="right")
    table.add_column("Result", justify="right")
    table.add_column("Error", justify="right")

    for idx, action in enumerate(strategy_plan.actions):
        row = [str(idx), action.type.name, str(action.address)]

        match action.state:
            case ActionState.PLANNED:
                state = "planned"

            case ActionState.IN_PROGRESS:
                state = "[cyan] in progress"

            case ActionState.FAILED:
                state = "[red] failed"

            case ActionState.DONE:
                state = "[green] done"

            case ActionState.CANCELLED:
                state = "[dim] cancelled"

            case _:
                raise ValueError(f"unknown state {action.state}")

        row.append(state)
        row.append("" if action.result is None else str(action.result))
        row.append("" if action.error is None else str(action.error))

        table.add_row(*row)

    CONSOLE.print(table)


@cli.command()
@click.option("-e", "--exist", is_flag=True, default=False)
@click.pass_obj
def artifacts(ctx: Context, exist: bool):
    """Shows all the artifacts."""
    strategy = prepare_strategy(ctx=ctx)

    table = Table(title="Artifacts")
    table.add_column("Address", justify="left", no_wrap=True)

    if exist:
        table.add_column("Exists", justify="right")

    for address, artifact in strategy.artifacts().items():
        row = [str(address)]

        if exist:
            with print_waiting(f"checking if artifact {address} exists"):
                exists = artifact.exists(ctx)

                row.append("[green] yes" if exists else "no")

        table.add_row(*row)

    CONSOLE.print(table)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
