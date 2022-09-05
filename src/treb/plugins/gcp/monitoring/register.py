"""Register the Docker plugin."""
from typing import Sequence, Type

from treb.core.check import Check
from treb.plugins.gcp.monitoring.checks import UptimeCheck


def namespace() -> str:
    """Returns the namespace for the GCP monitoring plugin."""
    return "gcp_cloudrun"


def checks() -> Sequence[Type[Check]]:
    """Returns all GCP monitoring checks."""
    return [UptimeCheck]
