"""Implementations of all the Cloud Run steps."""
import time

from attrs import define

from treb.core.context import Context
from treb.core.step import Step
from treb.utils import log, print_waiting


@define(frozen=True, kw_only=True)
class Wait(Step):
    """Blocks the deploy execution for a given period of time.

    Arguments:
        artifact: dependency of the previous step.
        duration: seconds to wait during the step execution.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "wait"

    duration: float

    def run(self, ctx: Context):
        with print_waiting(f"waiting for {self.duration} seconds"):
            time.sleep(self.duration)

        log(f"waited for {self.duration} seconds")

    def rollback(self, ctx: Context):
        pass
