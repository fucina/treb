"""Contains all the integrations with Git."""
from dulwich import porcelain
from dulwich.repo import Repo


def get_current_commit(path: str) -> str:
    """Returns the SHA commit for the current HEAD.

    Arguments:
        path: path to the repository's directory.

    Returns:
        The head's commit SHA.
    """
    repo = Repo(path)

    return repo.head().decode("utf-8")


def commit(path: str, message: str) -> str:
    """Commits a change in the given repository.

    Arguments:
        path: path to the repository's directory.
    """
    repo = Repo(path)

    return porcelain.commit(repo, message.encode("utf-8"))


def push(path: str, remote_location: str):
    """Pushes a change to a remote repository.

    Arguments:
        path: path to the repository's directory.
        remote_location: location of the remote.
    """
    repo = Repo(path)

    porcelain.push(repo, remote_location)
