# Offline advisory decision contract (v1)

This component is a **read-only**, **offline** baseline-vs-candidate recommendation. It neither discovers CDN edges nor verifies routing/effective egress, and cannot authorize a DNS/hosts/WARP/PBR change.

Build from `go-spike/`:

```sh
GOPROXY=off go test ./internal/decision ./cmd/fastly-decision
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOARM64=v8.0 go build -trimpath -ldflags="-s -w" -o fastly-decision-arm64 ./cmd/fastly-decision
```

Input is a local JSON file only, maximum 1 MiB. Unknown/duplicate keys and trailing JSON are rejected.

```json
{
  "schema_version": 1,
  "baseline": {
    "service": "github", "ip": "8.8.8.8",
    "sample_count": 6, "failures": 0, "median_ms": 100,
    "p95_ms": 200, "tls_verified": true
  },
  "candidates": [
    {
      "service": "github", "ip": "9.9.9.9",
      "sample_count": 6, "failures": 0, "median_ms": 70,
      "p95_ms": 120, "tls_verified": true
    }
  ]
}
```

Example addresses above are **illustrative inputs**, not validated CDN candidates. The tool checks conservative public IPv4 eligibility but cannot prove IP ownership or service/CDN compatibility; downstream systems must treat the output as advisory only.

Possible `status`: `insufficient_evidence`, `keep_baseline`, `recommend_review`. Every output has `safe_to_apply: false`. Eligibility requires at least five samples per path, zero observed failures, TLS verification, the same service, and at least 15% improvement for both median and p95. Candidate ranking prioritizes p95 and uses a stable tie-break.

## Explicit limitations

- Samples are **caller-provided**. This is not an attestation mechanism and does not establish matched routes or reproducible workload.
- There is no authoritative target registry, POP verification, trusted candidate discovery, confidence estimation, hysteresis/cooldown or historical evidence aggregation yet.
- No automatic apply, unattended scanning, DNS writer, Router execution or live public probe is connected to this CLI.
- `recommend_review` means only that submitted metrics passed these basic guards; not that the destination is safe to use.
