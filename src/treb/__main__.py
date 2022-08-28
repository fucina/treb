"""Main entrypoint for the `treb` command."""
import json
import os
import sys

import click
import toml
from cattrs import structure, unstructure
from rich import print

from treb.core.artifact import ArtifactSpec
from treb.core.config import Config, load_config
from treb.core.context import Context
from treb.core.deploy import discover_deploy_files
from treb.core.state import load_state
from treb.core.step import Step
from treb.core.strategy import Plan, Strategy
from treb.utils import print_exception


@click.group()
def artifact():
    pass


@artifact.command()
def artifact_list():
    pass


def load_context(config: Config) -> Context:
    from treb.docker.artifact import DockerImageSpec
    from treb.docker.steps import DockerPull, DockerPush

    return Context(
        config=config,
        artifact_specs={
            "docker_image": DockerImageSpec,
            "docker_pull": DockerPull,
            "docker_push": DockerPush,
        },
        revision="438a0191f73ea8a77ad2d88b4fc8613a52cec5cc",
    )


def dump_plan(path: str, plan: Plan):
    with open(path, "w") as fp:
        encoded = unstructure(plan)
        fp.write(json.dumps(encoded))


def load_plan(path: str) -> Plan:
    with open(path) as fp:
        decoded = json.loads(fp.read())

        print(decoded)
        return structure(decoded, Plan)


def run():
    """Entrypoint for every `treb` execution from the command line."""
    config = load_config(sys.argv[1])

    if len(sys.argv) > 2:
        plan_path = sys.argv[2]

    else:
        plan_path = None

    ctx = load_context(config=config)
    state = load_state(ctx)

    print(config)
    print(ctx)
    print(state)

    for name, project in ctx.config.projects.items():
        strategy = Strategy(ctx)

        for deploy_file in discover_deploy_files(
            root=project.repo_path, deploy_filename=ctx.config.deploy_filename
        ):
            base = os.path.normpath(os.path.dirname(deploy_file.path))

            def register_step(step):
                strategy.register_step(base, step)

            def register_artifact(artifact):
                strategy.register_artifact(base, artifact)

            Step.register_callback(register_step)
            ArtifactSpec.register_callback(register_artifact)

            exec_globals = {**ctx.artifact_specs}
            try:
                exec(
                    deploy_file.code,
                    exec_globals,
                )

            except Exception as exc:
                print_exception(f"failed during a deploy file execution: {deploy_file.path}")

            Step.unregister_callback(register_step)
            ArtifactSpec.unregister_callback(register_artifact)

        print("artifacts:", strategy._artifacts)
        print("steps:", strategy._steps)
        print("graph:", strategy._graph)
        print("rev graph:", strategy._rev_graph)

        if plan_path:
            print("loading existing plan")
            plan = load_plan(plan_path)

        else:
            print("creating a new plan")
            plan = strategy.plan()

        print("executing plan:", plan)

        for curr_plan in strategy.execute(plan):
            print("===")
            print(curr_plan)
            dump_plan(f"/tmp/{ctx.revision}", curr_plan)


if __name__ == "__main__":
    run()
