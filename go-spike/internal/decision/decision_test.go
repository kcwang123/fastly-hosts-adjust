package decision

import "testing"

func sample(ip string,med,p95 float64) Sample {
 return Sample{Service:"github",IP:ip,Count:6,Failures:0,MedianMS:med,P95MS:p95,TLSVerified:true}
}
func TestEvaluateSafetyGates(t *testing.T){
 base:=sample("8.8.8.8",100,200)
 tests:=[]struct{name string; baseline Sample; candidates []Sample; status,ip string}{
  {"good",base,[]Sample{sample("9.9.9.9",70,130)},"recommend_review","9.9.9.9"},
  {"weak_improvement",base,[]Sample{sample("9.9.9.9",90,185)},"keep_baseline",""},
  {"tail_regression",base,[]Sample{sample("9.9.9.9",60,201)},"keep_baseline",""},
  {"different_service",base,[]Sample{{Service:"twitch",IP:"9.9.9.9",Count:6,TLSVerified:true,MedianMS:10,P95MS:30}},"keep_baseline",""},
  {"baseline_error",Sample{Service:"github",IP:"8.8.8.8",Count:6,Failures:1,MedianMS:100,P95MS:200,TLSVerified:true},[]Sample{sample("9.9.9.9",10,20)},"insufficient_evidence",""},
  {"missing_samples",base,[]Sample{{Service:"github",IP:"9.9.9.9",Count:1,MedianMS:10,P95MS:20,TLSVerified:true}},"keep_baseline",""},
  {"unverified_tls",base,[]Sample{{Service:"github",IP:"9.9.9.9",Count:6,MedianMS:10,P95MS:20}},"keep_baseline",""},
  {"invalid_candidate_ip",base,[]Sample{sample("192.168.1.1",10,20)},"keep_baseline",""},
  {"shared_address",base,[]Sample{sample("100.64.0.1",10,20)},"keep_baseline",""},
  {"candidate_failures",base,[]Sample{{Service:"github",IP:"9.9.9.9",Count:6,Failures:1,MedianMS:10,P95MS:20,TLSVerified:true}},"keep_baseline",""},
  {"invalid_baseline_ip",sample("127.0.0.1",100,200),[]Sample{sample("9.9.9.9",10,20)},"insufficient_evidence",""},
 }
 for _,tc:=range tests {t.Run(tc.name,func(t *testing.T){
  got,err:=Evaluate(tc.baseline,tc.candidates)
  if err!=nil||got.Status!=tc.status||got.CandidateIP!=tc.ip||got.SafeToApply {t.Fatalf("result %+v err %v",got,err)}
 })}
}
func TestTooManyCandidates(t *testing.T){
 candidates:=make([]Sample,21)
 if _,err:=Evaluate(sample("8.8.8.8",100,200),candidates);err==nil{t.Fatal("unbounded candidates accepted")}
}
func TestRankByP95(t *testing.T){
 a:=sample("9.9.9.9",60,140)
 b:=sample("1.1.1.1",70,120)
 got,err:=Evaluate(sample("8.8.8.8",100,200),[]Sample{a,b})
 if err!=nil||got.CandidateIP!=b.IP {t.Fatalf("unexpected %+v, %v",got,err)}
}
