package main

import "testing"

func TestDecisionContract(t *testing.T){
 cases:=[]struct{name,json,status string; reject bool}{
  {"valid",`{"schema_version":1,"baseline":{"service":"github","ip":"8.8.8.8","sample_count":5,"median_ms":100,"p95_ms":200,"tls_verified":true},"candidates":[{"service":"github","ip":"9.9.9.9","sample_count":5,"median_ms":70,"p95_ms":100,"tls_verified":true}]}`,"recommend_review",false},
  {"unsupported_version",`{"schema_version":2,"baseline":{},"candidates":[]}`,"",true},
  {"duplicate",`{"schema_version":1,"schema_version":1,"baseline":{},"candidates":[]}`,"",true},
  {"unknown",`{"schema_version":1,"baseline":{},"candidates":[],"write_dns":true}`,"",true},
  {"no_candidates",`{"schema_version":1,"baseline":{}}`,"",true},
  {"trailing",`{"schema_version":1,"baseline":{},"candidates":[]}{}`,"",true},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  out,err:=evaluate([]byte(tc.json))
  if (err!=nil)!=tc.reject {t.Fatalf("unexpected err %v",err)}
  if !tc.reject && (out.Status!=tc.status||out.SafeToApply){t.Fatalf("unexpected %+v",out)}
 })}
}
