"""All the steps provided by the docker system."""
from typing import Optional

import CloudFlare
from attrs import define

from treb.core.context import Context
from treb.core.step import Step
from treb.utils import print_waiting

CLIENT = CloudFlare.CloudFlare(raw=True)


@define(frozen=True, kw_only=True)
class DnsRecordData:
    """Represents the configuration of Cloudflare DNS record.

    Arguments:
        record_type: DNS record type (i.e. `A`, `AAA`).
        record_name: DNS record name.
        content: DNS record content
        ttl: Time to live, in seconds, of the DNS record.
        proxied: Whether the record is receiving the performance and security
            benefits of Cloudflare.
    """

    type: str
    name: str
    content: str
    ttl: int
    proxied: Optional[bool] = None


@define(frozen=True, kw_only=True)
class DnsRecord:
    """Represents a Cloudflare DNS record.

    Arguments:
        id: identifier assigned by Cloudflare to this record.
        data: the data of a DNS record.
    """

    id: str
    data: DnsRecordData


@define(frozen=True, kw_only=True)
class CloudflareUpdateDnsResult:
    """Results of the step `CloudflareUpdateDns` containing the new DNS record
    configuration.

    Arguments:
        record: the new DNS record.
    """

    record: DnsRecord


def _find_record(zone_id: str, name: str) -> Optional[DnsRecord]:
    resp = CLIENT.zones.dns_records.get(zone_id)
    for dns_record in resp["result"]:
        if dns_record["name"] == name:

            return DnsRecord(
                id=dns_record["id"],
                data=DnsRecordData(
                    type=dns_record["type"],
                    name=dns_record["name"],
                    content=dns_record["content"],
                    ttl=dns_record["ttl"],
                    proxied=dns_record["proxied"],
                ),
            )

    return None


@define(frozen=True, kw_only=True)
class CloudflareUpdateDns(Step):
    """Updates a DNS record on Cloudflare.

    Arguments:
        zone_id: identifier of the zone for the DNS record.
        record: the new DNS record.
    """

    @classmethod
    def spec_name(cls) -> str:
        return "cloudflare_update_dns"

    zone_id: str
    record: DnsRecordData

    def snapshot(self, ctx: Context) -> Optional[DnsRecord]:
        with print_waiting("finding existing dns record"):
            return _find_record(self.zone_id, self.record.name)

    def run(self, ctx: Context, snapshot: Optional[DnsRecord]) -> CloudflareUpdateDnsResult:
        req = {
            "type": self.record.type,
            "name": self.record.name,
            "content": self.record.content,
            "ttl": self.record.ttl,
        }

        if self.record.proxied is not None:
            req["proxied"] = self.record.proxied

        if snapshot is None:
            with print_waiting("creating new dns record"):
                resp = CLIENT.zones.dns_records.post(self.zone_id, data=req)

        else:
            with print_waiting("updating dns record"):
                resp = CLIENT.zones.dns_records.patch(self.zone_id, snapshot.id, data=req)

        res = resp["result"]

        return CloudflareUpdateDnsResult(
            record=DnsRecord(
                id=res["id"],
                data=DnsRecordData(
                    type=res["type"],
                    name=res["name"],
                    content=res["content"],
                    ttl=res["ttl"],
                    proxied=res["proxied"],
                ),
            )
        )

    def rollback(self, ctx: Context, snapshot: Optional[DnsRecord]):
        if snapshot is None:
            record = _find_record(self.zone_id, self.record.name)
            if record is None:
                return

            CLIENT.zones.dns_records.delete(self.zone_id, record.id)

        else:
            req = {
                "type": snapshot.data.type,
                "name": snapshot.data.name,
                "content": snapshot.data.content,
                "ttl": snapshot.data.ttl,
            }

            if self.record.proxied is not None:
                req["proxied"] = self.record.proxied

            with print_waiting("updating dns record"):
                CLIENT.zones.dns_records.patch(self.zone_id, snapshot.id, data=req)
