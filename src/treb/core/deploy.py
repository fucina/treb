import os
from pathlib import Path
from typing import Iterator

from attrs import define


@define(frozen=True, kw_only=True)
class DeployFile:
    path: str
    code: str


def discover_deploy_files(root: Path, deploy_filename: str) -> Iterator[DeployFile]:
    for (dirpath, dirnames, filenames) in os.walk(root):
        for filename in filenames:
            if filename != deploy_filename:
                continue

            path = os.path.join(dirpath, filename)

            with open(path) as fp:
                code = fp.read()

            yield DeployFile(
                path=path,
                code=code,
            )
