"""Implementation artifacts used to represt Docker images."""
from typing import Optional
from urllib.parse import urlparse

import CloudFlare
from attrs import define

from treb.core.artifact import Artifact
from treb.core.context import Context

CLIENT = CloudFlare.CloudFlare(raw=True)


@define(frozen=True, kw_only=True)
class PagesDeployment:
    """An artifact representing a Cloudflare Pages Deployment."""

    spec: "PagesDeploymentSpec"
    account_id: str
    project_name: str
    deployment_id: str
    url: str

    @property
    def url_hostname(self) -> str:
        """Returns the hostname of the deployment's URL."""
        url = urlparse(self.url)

        return url.hostname or ""


@define(frozen=True, kw_only=True)
class PagesDeploymentSpec(Artifact):
    """An artifact spec used to reference a Cloudflare Pages deployment.

    Arguments:
        account: the Cloudflare account ID for this project.
        project: the Pages project's name.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "cloudflare_pages_deployment"

    account_id: str
    project_name: str

    def resolve(self, ctx: Context) -> Optional[PagesDeployment]:
        page_number = 1

        while True:
            resp = CLIENT.accounts.pages.projects.deployments.get(
                self.account_id,
                self.project_name,
                params={
                    "page": page_number,
                    "per_page": 25,
                },
            )

            for deployment in resp["result"]:
                commit_hash = deployment["deployment_trigger"]["metadata"]["commit_hash"]
                if commit_hash == ctx.revision:
                    return PagesDeployment(
                        spec=self,
                        account_id=self.account_id,
                        project_name=self.project_name,
                        deployment_id=deployment["id"],
                        url=deployment["url"],
                    )

            count = resp["result_info"]["per_page"] * (page_number - 1) + len(resp["result"])
            if count >= resp["result_info"]["total_count"]:
                break

            page_number += 1

        return None
