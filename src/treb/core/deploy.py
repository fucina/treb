"""Funtions and data structures used to discover and manage deploy files."""
import os
from pathlib import Path
from typing import Iterator

from attrs import define


class Vars(dict):
    """Wraps a dictionary and provide access to the values using their keys as
    attribute names.

    This class is used to support variables within deploy files.
    """

    def __getattr__(self, name):
        if name in self:
            return self[name]

        raise AttributeError("No such attribute: " + name)


@define(frozen=True, kw_only=True)
class DeployFile:
    """A deploy file loaded from the repository.

    Arguments:
        path: the deploy file's path.
        code: the Python code loaded from the deploy file.
    """

    path: str
    code: str


def discover_deploy_files(
    root: Path | str,
    deploy_filename: str = "DEPLOY",
) -> Iterator[DeployFile]:
    """Finds all the deploy files in a directory and visit all the the
    subdirectories recursively.

    The content of the file is expected to be encoded using UTF-8.

    ⚠️ This function does not check if the deploy file is valid.

    Arguments:
        root: the directory where to start searching for the deploy files.
        deploy_filename: the name used for the deploy files.

    Yields:
        A deploy file found.
    """
    for (dirpath, _, filenames) in os.walk(root):
        for filename in filenames:
            if filename != deploy_filename:
                continue

            path = os.path.join(dirpath, filename)

            with open(path, encoding="utf-8") as file_deploy:
                code = file_deploy.read()

            yield DeployFile(
                path=path,
                code=code,
            )
