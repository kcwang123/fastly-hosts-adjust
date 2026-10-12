"""Validate benchmark schema v3 by independently recomputing every derived value.

Legacy schema v2 remains supported only by speed_contract for read-only
diagnostics; v2 cannot pass the Runner's v3 verification gate.
"""
import ipaddress
import math
import statistics
from speed_contract import check_evidence
from tls_verify import SERVICES

def verify(bundle, settings):
    if not isinstance(bundle,dict) or set(bundle)!={"schema_version","evidence","evaluation","diagnostics","dry_run","samples"}:
        raise ValueError("v3 envelope required")
    if bundle["schema_version"] != 3 or bundle["dry_run"] is not True:
        raise ValueError("read-only v3 evidence required")
    rows=bundle["samples"]
    if not isinstance(rows,list) or len(rows)!=2*settings.benchmark_rounds:
        raise ValueError("missing complete per-round observations")
    measurements={"baseline_mbps":[],"candidate_mbps":[]}
    etags=[];cache=[];total=0;domain=None;candidate=None
    for row in rows:
        required={"round","label","domain","ip","sni_domain","tls_verified","status",
                  "etag","cache_state","content_range","content_length",
                  "bytes","duration_seconds","mbps"}
        if not isinstance(row,dict) or set(row)!=required:
            raise ValueError("incomplete v3 observation")
        n=row["round"];label=row["label"]
        if type(n)!=int or not 0<=n<settings.benchmark_rounds or label not in ("baseline","candidate"):
            raise ValueError("invalid round or label")
        if row["domain"] not in SERVICES or row["sni_domain"]!=row["domain"] or row["tls_verified"] is not True:
            raise ValueError("untrusted TLS/SNI")
        if domain is None: domain=row["domain"]
        if domain!=row["domain"]: raise ValueError("mixed benchmark domain")
        ip=ipaddress.ip_address(row["ip"])
        if ip.version!=4 or not ip.is_global:raise ValueError("invalid destination")
        if label=="candidate":
            if candidate is None:candidate=row["ip"]
            if candidate!=row["ip"]:raise ValueError("mixed candidate")
        if row["status"]!=206 or type(row["bytes"])!=int or row["bytes"]!=settings.benchmark_sample_bytes:
            raise ValueError("invalid byte count or HTTP status")
        if row["content_length"] is not None and row["content_length"]!=row["bytes"]:
            raise ValueError("Content-Length disagreement")
        cr=row["content_range"]
        import re
        match=re.fullmatch(r"bytes 0-(\d+)/(\d+|\*)",cr) if isinstance(cr,str) else None
        if not match or int(match[1])!=row["bytes"]-1 or (match[2]!="*" and int(match[2])<row["bytes"]):
            raise ValueError("Content-Range disagreement")
        duration=row["duration_seconds"];speed=row["mbps"]
        if (type(duration) not in (int,float) or not math.isfinite(duration) or duration<=0 or
            type(speed) not in (int,float) or not math.isfinite(speed) or speed<=0 or
            not math.isclose(speed,row["bytes"]*8/duration/1000000,rel_tol=0.00001)):
            raise ValueError("inconsistent measured throughput")
        measurements[label+"_mbps"].append(speed)
        etag=row["etag"]
        if etag is not None and (not isinstance(etag,str) or not etag or len(etag)>256):
            raise ValueError("malformed ETag")
        if row["cache_state"] not in ("HIT","MISS","UNKNOWN"):raise ValueError("invalid cache state")
        etags.append(etag);cache.append(row["cache_state"]);total+=row["bytes"]
    expected={(n,label) for n in range(settings.benchmark_rounds) for label in ("baseline","candidate")}
    if {(r["round"],r["label"]) for r in rows}!=expected:raise ValueError("duplicate or missing samples")
    for label in ("baseline","candidate"):
        addresses={r["ip"] for r in rows if r["label"]==label}
        if len(addresses)!=1:raise ValueError("changing route address")
    if rows[0]["ip"]==candidate and all(r["ip"]==candidate for r in rows):
        raise ValueError("baseline equals candidate")
    if any(x is not None for x in etags) and (None in etags or len(set(etags))!=1):
        raise ValueError("ETag mismatch")
    known=[x for x in cache if x!="UNKNOWN"]
    if known and (len(known)!=len(cache) or len(set(known))!=1):
        raise ValueError("Cache mismatch")
    cv={label:100*statistics.pstdev(values)/statistics.mean(values) for label,values in measurements.items()}
    if any(x>settings.max_sample_cv_percent for x in cv.values()):raise ValueError("unstable samples")
    if total>settings.max_benchmark_bytes:raise ValueError("sample budget exceeded")
    raw={"schema_version":2,"safe_to_apply":False,"bytes_downloaded":total,
        "measurements":[{"domain":domain,"ip":candidate,"sni_domain":domain,"tls_verified":True,
        "http_status":206,**measurements}]}
    evaluated=check_evidence(raw,max_bytes=settings.max_benchmark_bytes,
        min_improvement_percent=settings.min_improvement_percent,minimum_rounds=settings.benchmark_rounds)
    diag={"cv_percent":cv,"etag":etags[0],"cache_state":cache[0]}
    if bundle["evidence"]!=raw or bundle["evaluation"]!=evaluated:
        raise ValueError("derived performance evidence mismatch")
    present=bundle["diagnostics"]
    if not isinstance(present,dict) or set(present)!=set(diag):
        raise ValueError("diagnostics mismatch")
    if any(not math.isclose(present["cv_percent"][k],cv[k],rel_tol=1e-8,abs_tol=1e-8) for k in cv):
        raise ValueError("CV mismatch")
    if present["etag"]!=diag["etag"] or present["cache_state"]!=diag["cache_state"]:
        raise ValueError("ETag/Cache summary mismatch")
    return evaluated
