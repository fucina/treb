"""Implementation of the resources used to represent Cloud Run services."""
from typing import Optional
from urllib.parse import urlparse, urlunparse

from attrs import define
from google.cloud import run_v2

from treb.core.context import Context
from treb.core.resource import Resource
from treb.utils import print_waiting

CLIENT = run_v2.ServicesClient()


@define(frozen=True, kw_only=True)
class CloudRunService:
    """A resource representing a Cloud Run Service on GCP."""

    service_name: str
    revision_id: str
    uri: str

    def latest_uri(self) -> str:
        """Creates the URI for the app serving from the target revision."""
        uri = urlparse(self.uri)
        uri = uri._replace(netloc=f"latest---{uri.netloc}")

        return urlunparse(uri)

    def previous_uri(self) -> str:
        """Creates the URI for the app serving from the previous revision."""
        uri = urlparse(self.uri)
        uri = uri._replace(netloc=f"previous---{uri.netloc}")

        return urlunparse(uri)


@define(frozen=True, kw_only=True)
class CloudRunServiceSpec(Resource):
    """A resource spec used to reference a Cloud Run Service on GCP.

    Arguments:
        image_name: the name of the image without the tag.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "gcp_cloudrun_service"

    service_name: str

    def state(self, ctx: Context) -> Optional[CloudRunService]:
        with print_waiting("fetching cloudrun service info"):
            request = run_v2.GetServiceRequest(
                name=self.service_name,
            )
            service = CLIENT.get_service(request)

        return CloudRunService(
            service_name=service.service_name,
            revision_id=service.template.revision,
            uri=service.uri,
        )
