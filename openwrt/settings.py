"""Validated OpenWrt scheduler configuration. No DNS modifications."""
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    health_interval_hours: int = 3
    benchmark_interval_hours: int = 24
    connect_timeout_seconds: float = 3.0
    api_timeout_seconds: float = 8.0
    process_timeout_seconds: int = 900
    retry_count: int = 2
    retry_delay_seconds: int = 15
    lock_stale_seconds: int = 1800
    max_benchmark_bytes: int = 360000000
    benchmark_rounds: int = 3
    benchmark_sample_bytes: int = 262144
    benchmark_workers: int = 1
    benchmark_deadline_seconds: int = 120
    benchmark_targets: tuple = ()
    auto_benchmark: bool = False
    egress_evidence_path: str = ""
    max_egress_age_seconds: int = 3600
    max_scan_age_seconds: int = 14400
    trusted_baselines: dict = None
    benchmark_read_timeout_seconds: float = 5.0
    min_improvement_percent: float = 15.0
    max_sample_cv_percent: float = 35.0
    failure_threshold: int = 2
    ownership_registry_path: str = "/etc/fastly-optimizer/ownership.json"
    transaction_snapshot_path: str = "/etc/fastly-optimizer/pending-transaction.json"
    dry_run: bool = True
    enabled_services: tuple = ("github", "x", "twitch")

    @classmethod
    def load(cls, path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("config must be an object")
        allowed = set(cls.__dataclass_fields__)
        if set(payload) - allowed:
            raise ValueError("unknown config parameters: " + ", ".join(sorted(set(payload)-allowed)))
        if "enabled_services" in payload:
            s = payload["enabled_services"]
            if not isinstance(s, list) or not s or len(set(s)) != len(s) or not set(s) <= {"github", "x", "twitch"}:
                raise ValueError("invalid enabled_services")
            payload["enabled_services"] = tuple(s)
        if "benchmark_targets" in payload:
            targets = payload["benchmark_targets"]
            if not isinstance(targets, list):
                raise ValueError("benchmark_targets must be a list")
            from ipaddress import ip_address
            from tls_verify import SERVICES
            clean = []
            for target in targets:
                if not isinstance(target, dict) or set(target) != {"domain", "baseline_ip", "candidate_ip"}:
                    raise ValueError("invalid benchmark target")
                if target["domain"] not in SERVICES:
                    raise ValueError("unapproved benchmark domain")
                for key in ("baseline_ip", "candidate_ip"):
                    ip = ip_address(target[key])
                    if ip.version != 4 or not ip.is_global:
                        raise ValueError("benchmark target must use public IPv4")
                if target["baseline_ip"] == target["candidate_ip"]:
                    raise ValueError("baseline equals candidate")
                clean.append(target)
            payload["benchmark_targets"] = tuple(clean)
        if "trusted_baselines" in payload:
            from ipaddress import ip_address
            from tls_verify import SERVICES
            baselines = payload["trusted_baselines"]
            if not isinstance(baselines, dict):
                raise ValueError("trusted_baselines must be a mapping")
            for domain, ipstr in baselines.items():
                if domain not in SERVICES or not isinstance(ipstr, str):
                    raise ValueError("unapproved baseline")
                ip = ip_address(ipstr)
                if ip.version != 4 or not ip.is_global:
                    raise ValueError("baseline must be public IPv4")
        obj = cls(**payload)
        for key in ("health_interval_hours", "benchmark_interval_hours", "process_timeout_seconds",
                    "retry_count", "retry_delay_seconds", "lock_stale_seconds",
                    "max_benchmark_bytes", "benchmark_rounds", "benchmark_sample_bytes",
                    "benchmark_workers", "benchmark_deadline_seconds", "max_scan_age_seconds", "max_egress_age_seconds", "failure_threshold"):
            value = getattr(obj, key)
            minimum = 0 if key in ("retry_count", "retry_delay_seconds") else 1
            if type(value) is not int or value < minimum:
                raise ValueError(key + " must be an integer >= " + str(minimum))
        for key in ("connect_timeout_seconds", "api_timeout_seconds",
                    "benchmark_read_timeout_seconds", "min_improvement_percent", "max_sample_cv_percent"):
            value = getattr(obj, key)
            if type(value) not in (float, int) or not (0 < value <= (100 if key == "min_improvement_percent" else 300)):
                raise ValueError("invalid " + key)
        for key in ("ownership_registry_path", "transaction_snapshot_path"):
            value = getattr(obj, key)
            if not isinstance(value, str) or not value.startswith("/etc/fastly-optimizer/") or ".." in value:
                raise ValueError("unsafe state path: " + key)
        if obj.ownership_registry_path == obj.transaction_snapshot_path:
            raise ValueError("transaction state paths must differ")
        if not 3 <= obj.benchmark_rounds <= 20 or not 1 <= obj.benchmark_workers <= 4:
            raise ValueError("unsupported benchmark workload")
        if obj.benchmark_sample_bytes > obj.max_benchmark_bytes:
            raise ValueError("sample exceeds total benchmark budget")
        if obj.benchmark_workers != 1:
            raise ValueError("parallel benchmark workers are not implemented; use 1")
        if obj.benchmark_deadline_seconds > obj.process_timeout_seconds:
            raise ValueError("benchmark deadline exceeds process timeout")
        if type(obj.egress_evidence_path) is not str:
            raise ValueError("egress_evidence_path must be a string")
        if obj.auto_benchmark and not obj.egress_evidence_path.startswith("/etc/fastly-optimizer/"):
            raise ValueError("auto benchmarking requires persistent egress evidence path")
        if type(obj.auto_benchmark) is not bool:
            raise ValueError("auto_benchmark must be boolean")
        if obj.auto_benchmark and (not obj.dry_run or not obj.trusted_baselines):
            raise ValueError("automatic benchmarks require dry_run and explicit trusted baselines")
        if type(obj.dry_run) is not bool:
            raise ValueError("dry_run must be boolean")
        if obj.benchmark_interval_hours < obj.health_interval_hours:
            raise ValueError("benchmark interval must not be shorter than health interval")
        if obj.process_timeout_seconds >= obj.lock_stale_seconds:
            raise ValueError("lock stale threshold must exceed process timeout")
        return obj

    def due(self, now_epoch, last_health_epoch=None, last_benchmark_epoch=None):
        def elapsed(last, hours):
            return last is None or now_epoch - last >= hours * 3600
        return {"health": elapsed(last_health_epoch, self.health_interval_hours),
                "benchmark": elapsed(last_benchmark_epoch, self.benchmark_interval_hours)}
