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
    min_improvement_percent: float = 15.0
    failure_threshold: int = 2
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
        obj = cls(**payload)
        for key in ("health_interval_hours", "benchmark_interval_hours", "process_timeout_seconds",
                    "retry_count", "retry_delay_seconds", "lock_stale_seconds",
                    "max_benchmark_bytes", "failure_threshold"):
            value = getattr(obj, key)
            minimum = 0 if key in ("retry_count", "retry_delay_seconds") else 1
            if type(value) is not int or value < minimum:
                raise ValueError(key + " must be an integer >= " + str(minimum))
        for key in ("connect_timeout_seconds", "api_timeout_seconds", "min_improvement_percent"):
            value = getattr(obj, key)
            if type(value) not in (float, int) or not (0 < value <= (100 if key == "min_improvement_percent" else 300)):
                raise ValueError("invalid " + key)
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
