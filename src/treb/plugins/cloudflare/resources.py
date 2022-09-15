"""Implementation artifacts used to represt Docker images."""
from typing import Optional

import CloudFlare
from attrs import define

from treb.core.context import Context
from treb.core.resource import Resource

CLIENT = CloudFlare.CloudFlare(raw=True)


@define(frozen=True, kw_only=True)
class PagesProject:
    """An artifact representing a Cloudflare Pages project."""

    subdomain: str


@define(frozen=True, kw_only=True)
class PagesProjectSpec(Resource):
    """An artifact spec used to reference a Cloudflare Pages project.

    Arguments:
        account: the Cloudflare account ID for this project.
        project_name: the Pages project's name.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "cloudflare_pages_project"

    account_id: str
    project_name: str

    def state(self, ctx: Context) -> Optional[PagesProject]:
        try:
            resp = CLIENT.accounts.pages.projects.get(
                self.account_id,
                self.project_name,
            )

            return PagesProject(
                subdomain=resp["subdomain"],
            )

        except CloudFlare.exceptions.CloudFlareAPIError as exc:
            # Error code: Project not found
            if int(exc) == 8000007:
                return None

            raise
