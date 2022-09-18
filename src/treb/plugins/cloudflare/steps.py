"""All the steps provided by the docker system."""
from typing import Optional

import CloudFlare
from attrs import define

from treb.core.context import Context
from treb.core.step import Step
from treb.utils import print_waiting

CLIENT = CloudFlare.CloudFlare(raw=True)


@define(frozen=True, kw_only=True)
class CloudflareUpdateDnsResult:
    """Results of the step `CloudflareUpdateDns` containing the new DNS record
    configuration.

    Arguments:
        record_type: DNS record type (i.e. `A`, `AAA`).
        record_name: DNS record name.
        content: DNS record content
        ttl: Time to live, in seconds, of the DNS record.
        proxied: Whether the record is receiving the performance and security
            benefits of Cloudflare.
    """

    record_type: str
    record_name: str
    content: str
    ttl: int
    proxied: bool


@define(frozen=True, kw_only=True)
class CloudflareUpdateDns(Step):
    """Updates a DNS record on Cloudflare.

    Arguments:
        zone_id: identifier of the zone for the DNS record.
        record_type: DNS record type (i.e. `A`, `AAA`).
        record_name: DNS record name.
        content: DNS record content
        ttl: Time to live, in seconds, of the DNS record.
        proxied: Whether the record is receiving the performance and security
            benefits of Cloudflare.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "cloudflare_update_dns"

    zone_id: str
    record_type: str
    record_name: str
    content: str
    ttl: int
    priority: Optional[int] = None
    proxied: Optional[bool] = None

    def run(self, ctx: Context) -> CloudflareUpdateDnsResult:
        record_id = None

        with print_waiting("finding existing dns record"):
            resp = CLIENT.zones.dns_records.get(self.zone_id)
            for dns_record in resp["result"]:
                if dns_record["name"] == self.record_name:
                    record_id = dns_record["id"]
                    break

        req = {
            "type": self.record_type,
            "name": self.record_name,
            "content": self.content,
            "ttl": self.ttl,
        }

        if self.priority is not None:
            req["proxied"] = self.priority

        if self.proxied is not None:
            req["proxied"] = self.proxied

        if record_id is None:
            with print_waiting("creating new dns record"):
                resp = CLIENT.zones.dns_records.post(self.zone_id, data=req)

        else:
            with print_waiting("updating dns record"):
                resp = CLIENT.zones.dns_records.patch(self.zone_id, record_id, data=req)

        res = resp["result"]

        return CloudflareUpdateDnsResult(
            record_type=res["type"],
            record_name=res["name"],
            content=res["content"],
            ttl=res["ttl"],
            proxied=res["proxied"],
        )

    def rollback(self, ctx: Context):
        pass
