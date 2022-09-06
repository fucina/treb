"""Implementation artifacts used to represt Docker images."""
from urllib.parse import urlparse, urlunparse

from attrs import define

from treb.core.artifact import Artifact, ArtifactSpec


@define(frozen=True, kw_only=True)
class CloudRunServiceArtifact(Artifact):
    """An artifact representing a Cloud Run Service on GCP."""

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
class CloudRunServiceSpec(ArtifactSpec):
    """An artifact spec used to reference a Cloud Run Service on GCP.

    Arguments:
        image_name: the name of the image without the tag.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "gcp_cloudrun_service"

    service_name: str
