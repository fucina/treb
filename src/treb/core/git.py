"""Contains all the integrations with Git."""
from dulwich.repo import Repo


def get_current_commit(path: str) -> str:
    """Returns the SHA commit for the current HEAD.

    Arguments:
        path: path to the repository's directory.

    Returns:
        The head's commit SHA.
    """
    repo = Repo(path)

    return repo.head()
