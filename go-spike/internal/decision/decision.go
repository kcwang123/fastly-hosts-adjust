// Package decision ranks read-only health evidence without authorizing DNS writes.
package decision

import (
 "errors"
 "math"
 "sort"
)

type Sample struct {
 Service string `json:"service"`
 IP string `json:"ip"`
 Count int `json:"sample_count"`
 Failures int `json:"failures"`
 MedianMS float64 `json:"median_ms"`
 P95MS float64 `json:"p95_ms"`
 TLSVerified bool `json:"tls_verified"`
}

type Recommendation struct {
 SchemaVersion int `json:"schema_version"`
 Status string `json:"status"`
 Reason string `json:"reason"`
 BaselineIP string `json:"baseline_ip"`
 CandidateIP string `json:"candidate_ip,omitempty"`
 ImprovementPercent float64 `json:"improvement_percent,omitempty"`
 SafeToApply bool `json:"safe_to_apply"`
}

const minSamples = 5
const minImprovementPercent = 15.0

func valid(s Sample) bool {
 return s.Service!="" && s.IP!="" && s.Count>=minSamples &&
  s.Failures>=0 && s.Failures<=s.Count && s.TLSVerified &&
  s.MedianMS>0 && s.P95MS>=s.MedianMS &&
  !math.IsNaN(s.MedianMS) && !math.IsInf(s.MedianMS,0) &&
  !math.IsNaN(s.P95MS) && !math.IsInf(s.P95MS,0)
}

// Evaluate is an advisory-only, deterministic safety gate. A candidate cannot
// win unless it has no observed failures and improves both median and p95.
func Evaluate(baseline Sample, candidates []Sample) (Recommendation,error) {
 out:=Recommendation{SchemaVersion:1,Status:"insufficient_evidence",Reason:"baseline insufficient",BaselineIP:baseline.IP,SafeToApply:false}
 if len(candidates)>20{return out,errors.New("too many candidates")}
 if !valid(baseline)||baseline.Failures!=0{return out,nil}
 eligible:=make([]Sample,0,len(candidates))
 for _,s:=range candidates {
  if s.Service!=baseline.Service||s.IP==baseline.IP||!valid(s)||s.Failures!=0 {continue}
  improvement:=100*(baseline.MedianMS-s.MedianMS)/baseline.MedianMS
  tailImprovement:=100*(baseline.P95MS-s.P95MS)/baseline.P95MS
  if improvement>=minImprovementPercent && tailImprovement>=minImprovementPercent {eligible=append(eligible,s)}
 }
 if len(eligible)==0 {out.Status="keep_baseline";out.Reason="no verified candidate exceeds threshold";return out,nil}
 sort.Slice(eligible,func(i,j int)bool{
  if eligible[i].P95MS!=eligible[j].P95MS{return eligible[i].P95MS<eligible[j].P95MS}
  if eligible[i].MedianMS!=eligible[j].MedianMS{return eligible[i].MedianMS<eligible[j].MedianMS}
  return eligible[i].IP<eligible[j].IP
 })
 best:=eligible[0]
 out.Status="recommend_review"
 out.Reason="verified latency improvement; manual review required"
 out.CandidateIP=best.IP
 out.ImprovementPercent=math.Round(1000*(baseline.MedianMS-best.MedianMS)/baseline.MedianMS)/10
 return out,nil
}
