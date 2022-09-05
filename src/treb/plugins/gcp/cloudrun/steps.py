"""Implementations of all the Cloud Run steps."""
import time
from typing import Dict, Mapping

from attrs import define
from cattrs import structure, unstructure
from google.cloud import run_v2

from treb.core.context import Context
from treb.core.step import Step
from treb.plugins.docker.artifacts import DockerImageArtifact
from treb.plugins.gcp.cloudrun.artifacts import CloudRunServiceArtifact, CloudRunServiceSpec
from treb.utils import log, print_waiting

CLIENT = run_v2.ServicesClient()

# namespace used when storing metadata in the resource annotations
ANNOTATION_NAMESPACE = "treb.fucina.dev"


@define(frozen=True, kw_only=True)
class ServiceAnnotations:
    """All the annotations used for storing metadata in a Cloud Run service.

    Arguments:
        revision: the target revision for the a deployment.
        previous_revision_id: the revions that will be replaced by this deployment.
    """

    revision: str
    previous_revision_id: str


def encode_annotations(annotations: ServiceAnnotations):
    """Creates a dictionary used to populate the service annotations.

    Arguments:
        annotations: the annotations to encode.

    Returns:
        The annotations in a dictionary (string to string).
    """
    return {
        f"{ANNOTATION_NAMESPACE}/{key}": str(value)
        for key, value in unstructure(annotations).items()
    }


def load_annotations(annotations: Mapping[str, str]) -> ServiceAnnotations:
    """Creates an instance of `ServiceAnnotations` from their dictionary form
    returned by the Cloud Run API.

    This function will discard any annotation that odesn't have the
    treb's namespace `trab.fucina.dev/`.

    Arguments:
        annotations: all theservice  annotations returned by the Cloud Run API.

    Returns:
        An instance of `ServiceAnnotations` representing the treb's
        custom annotations.
    """
    annotations = {
        key[len(ANNOTATION_NAMESPACE) + 1 :]: value
        for key, value in annotations.items()
        if key.startswith(ANNOTATION_NAMESPACE)
    }

    return structure(annotations, ServiceAnnotations)


def clean_annotations(annotations: Mapping[str, str]) -> Dict[str, str]:
    """Creates a dictionary from the given annotations discarding all the
    treb's annotations.

    Arguments:
        annotations: all the service annotations returned by the Cloud Run API.

    Returns:
        All the passed annotations minus the treb's ones.
    """
    return {
        key: value for key, value in annotations.items() if not key.startswith(ANNOTATION_NAMESPACE)
    }


def prepare_revision_id(revision: str, timestamp: int) -> str:
    """Generates a revision ID for a new Cloud Run service revision used to
    identify a service revision.

    The

    Arguments:
        service_name: the full service name.
        revision: the deployment revision.
        timestamp: when the revision has been created.

    Returns:
        The revision ID for the new service revision.
    """
    postfix = hex(timestamp)[2:].lower()

    return f"rev-{revision}-{postfix}"


@define(frozen=True, kw_only=True)
class CloudRunDeploy(Step):
    """Replaces the image of the service with the one built from the current
    revision.

    ## Deploy

    The new revision will start to serve 100% of the traffic
    immediately.

    ## Rollback

    Updates the service to use the revsion that was used before
    starting the deployment.

    Arguments:
        service: the GCP Cloud Run service to update.
        image: the new image to use in the Cloud Run service.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "gcp_cloudrun_deploy"

    service: CloudRunServiceSpec | CloudRunServiceArtifact
    image: DockerImageArtifact
    traffic_percent: int = 100

    def run(self, ctx: Context) -> CloudRunServiceArtifact:
        request = run_v2.GetServiceRequest(
            name=self.service.service_name,
        )
        service = CLIENT.get_service(request)

        if isinstance(self.service, CloudRunServiceSpec):
            annotations = ServiceAnnotations(
                revision=ctx.revision, previous_revision_id=service.template.revision
            )
            prev_revision_id = service.template.revision

            revision_id = prepare_revision_id(ctx.revision, int(time.time()))

            service.template.revision = revision_id
            service.template.containers[0].image = self.image.tag

            service.annotations = {
                **service.annotations,
                **encode_annotations(annotations),
            }

        elif isinstance(self.service, CloudRunServiceArtifact):
            annotations = load_annotations(service.annotations)

            prev_revision_id = annotations.previous_revision_id
            revision_id = service.template.revision

            service.template.containers[0].image = self.image.tag

        service.traffic = [
            run_v2.TrafficTarget(
                type_=(run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION),
                revision=revision_id,
                percent=min(self.traffic_percent, 100),
                tag="latest",
            ),
            run_v2.TrafficTarget(
                type_=(run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION),
                revision=prev_revision_id,
                percent=100 - self.traffic_percent,
                tag="previous",
            ),
        ]

        with print_waiting(f"deploying new service {service.name}"):
            log(
                f"creating a new service revision {revision_id} "
                f"serving {self.traffic_percent}% of the traffic"
            )

            request = run_v2.UpdateServiceRequest(service=service)

            operation = CLIENT.update_service(request=request)
            service = operation.result()

            log(f"created a new service revision {revision_id}")

        return CloudRunServiceArtifact(
            service_name=self.service.service_name,
            revision_id=service.template.revision,
            uri=service.uri,
        )

    def rollback(self, ctx):
        request = run_v2.GetServiceRequest(
            name=self.service.service_name,
        )
        service = CLIENT.get_service(request)
        annotations = load_annotations(service.annotations)

        service.annotations = clean_annotations(service.annotations)
        service.template.revision = annotations.previous_revision_id

        with print_waiting("rolling back service"):
            request = run_v2.UpdateServiceRequest(service=service)

            operation = CLIENT.update_service(request=request)
            service = operation.result()

            log(f"rolled back to service revision {annotations.previous_revision_id}")
