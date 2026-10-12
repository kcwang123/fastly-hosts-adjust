package scanner

import (
 "context"
 "encoding/json"
 "errors"
 "math"
 "time"
)

var services=map[string]string{"github":"raw.githubusercontent.com","x":"pbs.twimg.com","twitch":"static-cdn.jtvnw.net"}
type Target struct {Service string `json:"service"`; IP string `json:"ip"`}
type Candidate struct {Service string `json:"service"`; IP string `json:"ip"`; Pop string `json:"pop"`; LatencyMS float64 `json:"latency_ms"`}
type Output struct {
 SchemaVersion int `json:"schema_version"`
 Source string `json:"source"`
 Evidence string `json:"evidence"`
 SafeToApply bool `json:"safe_to_apply"`
 ScannedBlocks int `json:"scanned_blocks"`
 SkippedBlocks int `json:"skipped_blocks"`
 Candidates []Candidate `json:"candidates"`
}
type Probe func(context.Context,string,string)(string,time.Duration,error)
func Scan(ctx context.Context,targets []Target,probe Probe)([]byte,error){return ScanWithRetries(ctx,targets,probe,0)}
func ScanWithRetries(ctx context.Context,targets []Target,probe Probe,retries int)([]byte,error){
 if retries<0||retries>2{return nil,errors.New("invalid retry count")}
 if len(targets)==0||len(targets)>20||probe==nil{return nil,errors.New("bounded targets and injected probe required")}
 out:=Output{SchemaVersion:1,Source:"fastly-hosts-adjust",Evidence:"latency_only",Candidates:[]Candidate{}}
 for _,t:=range targets {
  domain,ok:=services[t.Service];if !ok{return nil,errors.New("unapproved service")}
  if !PublicIPv4(t.IP){return nil,errors.New("unapproved address")}
  // Fail the whole health observation on any failed or timed out probe.
  var pop string
  var elapsed time.Duration
  var err error
  var timeoutErr error
  for attempt:=0;attempt<=retries;attempt++{
   if ctx.Err()!=nil{return nil,ctx.Err()}
   bounded,cancel:=context.WithTimeout(ctx,3*time.Second)
   pop,elapsed,err=probe(bounded,domain,t.IP)
   timeoutErr=bounded.Err()
   cancel()
   if err==nil&&timeoutErr==nil&&pop!=""&&elapsed>0&&elapsed<=3*time.Second{break}
  }
  if err!=nil||timeoutErr!=nil||pop==""||elapsed<=0||elapsed>3*time.Second{return nil,errors.New("probe failed")}
  if ctx.Err()!=nil{return nil,ctx.Err()}
  ms:=math.Round(elapsed.Seconds()*1e5)/100
  if ms<=0||math.IsInf(ms,0)||math.IsNaN(ms){return nil,errors.New("invalid latency")}
  out.ScannedBlocks++
  out.Candidates=append(out.Candidates,Candidate{Service:t.Service,IP:t.IP,Pop:pop,LatencyMS:ms})
 }
 return json.Marshal(out)
}
