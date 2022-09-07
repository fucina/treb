"""Implementation of the deployment checks using GCP."""
import time
from datetime import datetime, timezone
from typing import Dict, Generic, List, Optional, TypeVar
from urllib.parse import urlparse

from attrs import define
from google.cloud import monitoring_v3

from treb.core.check import Check, FailedCheck
from treb.plugins.gcp.cloudrun.artifacts import CloudRunServiceArtifact
from treb.utils import log, print_waiting

UPTIME_CLIENT = monitoring_v3.UptimeCheckServiceClient()
METRICS_CLIENT = monitoring_v3.MetricServiceClient()


DatapointType = TypeVar("DatapointType")


@define(frozen=True, kw_only=True)
class Datapoint(Generic[DatapointType]):
    """A single datapoint in a time series.

    Arguments:
        start_time: start of the time interval to which the data point applies.
        end_time: end of the time interval to which the data point applies.
        value: value of the data point.
    """

    start_time: datetime
    end_time: datetime
    value: DatapointType


@define(frozen=True, kw_only=True)
class UptimeCheckResult:
    """All results from a Uptime Check in a given interval.

    Arguments:
        datapoints: all the datapoints generated by the Uptime Check.
    """

    datapoints: List[Datapoint]


@define(frozen=True, kw_only=True)
class UptimeCheck(Check):
    """Uses GCP Uptime Checks to evaluate a deployment health.

    The Uptime will _ping_ the given service with a HTTP(S)
    request periodically and use the response to track successful and
    failed checks.

    The checks failed if the number of failed checks is above the given
    threshold.

    Arguments:
        service: the GCP service to monitor.
        project: the GCP project where the Uptime Check will be created.
        method: the HTTP method to use for the Uptime Check.
        path: the path to add to the service URI when performing the Uptime Check.
        port: the path to add to the service URI when performing the Uptime Check.
            If set to `None`, it will default to the well-known port for HTTP/S.
        content_type: content type header to use for the check.
        body: request body associated with the HTTP request.
        headers: all headers to send as part of the Uptime check request.
        timeout: maximum amount of time to wait for the request to complete.
        period: how often, in seconds, the Uptime check is performed.
        min_datapoints: minimum number of datapoints needed before making a decision
            about the check result.
        max_datapoints: maximum number of datapoints needed before stopping the check.
        fail_threshold: minimum number of failed datapoints needed to mark a check as failed.
    """

    service: CloudRunServiceArtifact
    project: str

    method: str = "GET"
    path: str = "/"
    port: Optional[int] = None
    content_type: Optional[str] = None
    body: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout: int = 10
    period: int = 60

    min_datapoints: int = 3
    max_datapoints: int = 10
    fail_threshold: int = 3

    reuse: bool = True

    @classmethod
    def spec_name(cls) -> str:
        return "gcp_uptime_check"

    def parent(self) -> str:
        """Constructs the full project path for this Uptime Check."""
        return UPTIME_CLIENT.common_project_path(self.project)

    def _setup(self):
        display_name = f"[treb] uptime check service={self.service.service_name}"

        config = monitoring_v3.UptimeCheckConfig()
        is_new = True
        if self.reuse:
            request = monitoring_v3.ListUptimeCheckConfigsRequest(
                parent=self.parent(),
            )
            page_result = UPTIME_CLIENT.list_uptime_check_configs(request=request)

            for uptime_config in page_result:
                if uptime_config.display_name == display_name:
                    config = uptime_config
                    is_new = False
                    log(f"found existing uptime check {config.name}")
                    break

            else:
                log("creating a new uptime config")

        uri = urlparse(self.service.latest_uri())

        is_https = uri.scheme == "https"
        port = uri.port if self.port is None else self.port
        if port is None:
            port = 443 if is_https else 80

        config.display_name = display_name
        config.monitored_resource = {
            "type": "uptime_url",
            "labels": {"host": uri.hostname},
        }

        http_check = {
            "use_ssl": is_https,
            "request_method": monitoring_v3.UptimeCheckConfig.HttpCheck.RequestMethod[
                self.method.upper()
            ],
            "path": self.path,
            "port": self.port,
        }
        if self.content_type is not None:
            http_check["content_type"] = monitoring_v3.UptimeCheckConfig.HttpCheck.ContentType[
                self.content_type.upper()
            ]

        if self.body is not None:
            http_check["body"] = self.body

        if self.headers is not None:
            http_check["headers"] = self.headers

        config.http_check = http_check

        config.timeout = {"seconds": self.timeout}
        config.period = {"seconds": self.period}

        if is_new:
            new_config = UPTIME_CLIENT.create_uptime_check_config(
                request={
                    "parent": self.parent(),
                    "uptime_check_config": config,
                }
            )

        else:
            new_config = UPTIME_CLIENT.update_uptime_check_config(
                request={
                    "uptime_check_config": config,
                }
            )

        return new_config

    def _eval(self, check_id: str, start_time: datetime, end_time: datetime):
        interval = monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": int(end_time.timestamp()), "nanos": 0},
                "start_time": {"seconds": int(start_time.timestamp()), "nanos": 0},
            }
        )

        filter_query = " ".join(
            [
                'metric.type = "monitoring.googleapis.com/uptime_check/check_passed"',
                'resource.type = "uptime_url"',
                f'metric.label."check_id" = "{check_id}"',
            ]
        )

        results = METRICS_CLIENT.list_time_series(
            request={
                "name": METRICS_CLIENT.common_project_path(self.project),
                "filter": filter_query,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        datapoints = []

        for result in results:
            for point in result.points:
                datapoints.append(
                    Datapoint(
                        start_time=point.interval.start_time,
                        end_time=point.interval.end_time,
                        value=point.value.bool_value,
                    )
                )

        return UptimeCheckResult(
            datapoints=datapoints,
        )

    def check(self, ctx) -> CloudRunServiceArtifact:
        with print_waiting("setting up uptime check"):
            config = self._setup()

        try:
            with print_waiting("evaluating uptime check"):
                check_id = UPTIME_CLIENT.parse_uptime_check_config_path(config.name)[
                    "uptime_check_config"
                ]

                start_time = datetime.now(timezone.utc)
                failed = False

                while True:
                    time.sleep(self.period)

                    res = self._eval(
                        check_id=check_id,
                        start_time=start_time,
                        end_time=datetime.now(timezone.utc),
                    )

                    if len(res.datapoints) >= self.max_datapoints:
                        break

                    if len(res.datapoints) < self.min_datapoints:
                        continue

                    failed_datapoints = 0
                    for datapoint in res.datapoints:
                        if not datapoint.bool_value:
                            failed_datapoints += 1

                    if failed_datapoints >= self.fail_threshold:
                        failed = True
                        break

                if failed:
                    raise FailedCheck

        finally:
            if not self.reuse:
                with print_waiting("tearing down uptime check"):
                    request = monitoring_v3.DeleteUptimeCheckConfigRequest(
                        name=config.name,
                    )

                    UPTIME_CLIENT.delete_uptime_check_config(request=request)

        return self.service
