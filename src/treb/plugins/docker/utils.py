"""Helpers for deploying Docker images."""


def full_tag(image_name: str, tag_prefix: str, revision: str) -> str:
    """Creates the image full tag (image name + tag) for a specific revision.

    Argument:
        image_name: the image's name (i.e. `ghcr.io/fucina/treb`)
        tag_prefix: string prepended to the tag (i.e. `rev-`).
        revision: the revision identifier.

    Returns:
        The full image tag (i.e. `ghcr.io/fucina/treb:rev-abc`)
    """
    return f"{image_name}:{tag_prefix}{revision}"
