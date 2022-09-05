import time
from typing import Optional
from urllib.parse import urlparse

from attrs import define
from google.cloud import monitoring_v3

from treb.core.check import Check, FailedCheck
from treb.plugins.gcp.cloudrun.artifacts import CloudRunServiceArtifact
from treb.utils import log, print_waiting

UPTIME_CLIENT = monitoring_v3.UptimeCheckServiceClient()
METRICS_CLIENT = monitoring_v3.MetricServiceClient()


@define(frozen=True, kw_only=True)
class UptimeCheck(Check):

    service: CloudRunServiceArtifact
    project: str

    method: str = "GET"
    path: str = "/"
    port: str = 443
    content_type: Optional[str] = None
    body: Optional[str] = None

    timeout: int = 10
    period: int = 60
    wait_for: int = 5
    healthy_percent: float = 0.9

    @classmethod
    def spec_name(cls) -> str:
        return "gcp_uptime_check"

    def setup(self, ctx) -> CloudRunServiceArtifact:
        uri = urlparse(self.service.latest_uri())

        config = monitoring_v3.UptimeCheckConfig()
        config.display_name = f"[treb] Uptime check for {self.service.service_name}"
        config.monitored_resource = {
            "type": "uptime_url",
            "labels": {"host": uri.hostname},
        }

        http_check = {
            "use_ssl": uri.scheme == "https",
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

        config.http_check = http_check

        config.timeout = {"seconds": self.timeout}
        config.period = {"seconds": self.period}

        new_config = UPTIME_CLIENT.create_uptime_check_config(
            request={
                "parent": UPTIME_CLIENT.common_project_path(self.project),
                "uptime_check_config": config,
            }
        )

        return new_config

    def eval(self, check_id):
        interval = monitoring_v3.TimeInterval()

        wait_total = self.wait_for * self.period
        time.sleep(wait_total)

        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 10**9)
        interval = monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": seconds, "nanos": nanos},
                "start_time": {"seconds": (seconds - wait_total), "nanos": nanos},
            }
        )

        filter_query = " ".join(
            [
                'metric.type = "monitoring.googleapis.com/uptime_check/check_passed"',
                'resource.type = "uptime_url"',
                f'metric.label."check_id" = "{check_id}"',
            ]
        )

        print(filter_query)

        time.sleep(self.wait_for * self.period)

        results = METRICS_CLIENT.list_time_series(
            request={
                "name": METRICS_CLIENT.common_project_path(self.project),
                "filter": filter_query,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        total = 0
        success = 0

        for result in results:
            for point in result.points:
                total += 1
                if point.value.bool_value:
                    success += 1

        success_percent = success / total if total > 0 else 0.0

        if success_percent <= self.healthy_percent:
            log(f"failed uptime check ({success} / {total}, {success_percent * 100}%)")
            raise FailedCheck()

    def teardown(self, ctx, name):
        request = monitoring_v3.DeleteUptimeCheckConfigRequest(
            name=name,
        )

        UPTIME_CLIENT.delete_uptime_check_config(request=request)

    def check(self, ctx) -> CloudRunServiceArtifact:
        with print_waiting("setting up uptime check"):
            config = self.setup(ctx)

        try:
            with print_waiting("evaluating uptime check"):
                check_id = UPTIME_CLIENT.parse_uptime_check_config_path(config.name)[
                    "uptime_check_config"
                ]
                self.eval(check_id)

                log("passed uptime check")

        finally:
            with print_waiting("tearing down uptime check"):
                self.teardown(ctx, config.name)

        return self.service
