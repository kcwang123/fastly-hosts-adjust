package scheduler

import (
 "bytes"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "net"
)

type Config struct {
 DryRun bool `json:"dry_run"`
 AutoBenchmark bool `json:"auto_benchmark"`
 HealthHours int64 `json:"health_interval_hours"`
 BenchmarkHours int64 `json:"benchmark_interval_hours"`
}
type State struct {
 LastHealth *int64 `json:"last_health_epoch,omitempty"`
 LastBenchmark *int64 `json:"last_benchmark_epoch,omitempty"`
}
type Scan struct {
 SchemaVersion int `json:"schema_version"`
 Source string `json:"source"`
 Evidence string `json:"evidence"`
 SafeToApply bool `json:"safe_to_apply"`
 ScannedBlocks int `json:"scanned_blocks"`
 SkippedBlocks int `json:"skipped_blocks"`
 Candidates []Candidate `json:"candidates"`
}
type Candidate struct {
 Service string `json:"service"`
 IP string `json:"ip"`
 Pop string `json:"pop"`
 LatencyMS float64 `json:"latency_ms"`
}
func strict(data []byte,v any)error{
 d:=json.NewDecoder(bytes.NewReader(data));d.DisallowUnknownFields()
 if err:=d.Decode(v);err!=nil{return err}
 var extra any;if err:=d.Decode(&extra);err==nil{return errors.New("extra JSON")}else if err.Error()!="EOF"{return err}
 return nil
}
func LoadConfig(data []byte)(Config,error){
 var c Config
 if err:=strict(data,&c);err!=nil{return c,err}
 var fields map[string]json.RawMessage
 if err:=json.Unmarshal(data,&fields);err!=nil{return c,err}
 for _,k:=range []string{"dry_run","auto_benchmark"}{if _,ok:=fields[k];!ok{return c,errors.New("missing safety gate")}}
 if !c.DryRun||c.AutoBenchmark{return c,errors.New("unsafe configuration")}
 if c.HealthHours==0{c.HealthHours=3};if c.BenchmarkHours==0{c.BenchmarkHours=24}
 if c.HealthHours<1||c.BenchmarkHours<c.HealthHours{return c,errors.New("invalid intervals")}
 return c,nil
}
func LoadState(data []byte)(State,error){
 if len(data)==0{return State{},nil}
 var s State;if err:=strict(data,&s);err!=nil{return s,err}
 for _,v:=range []*int64{s.LastHealth,s.LastBenchmark}{if v!=nil&&*v<0{return s,errors.New("negative timestamp")}}
 return s,nil
}
func due(now int64,last *int64,hours int64)bool{return last==nil||now-*last>=hours*3600}
func Mode(c Config,s State,now int64)string{
 if due(now,s.LastHealth,c.HealthHours){return "health"}
 if due(now,s.LastBenchmark,c.BenchmarkHours){return "benchmark_pending"}
 return "skip"
}
func ValidateScan(data []byte)error{
 var s Scan;if err:=strict(data,&s);err!=nil{return err}
 if s.SchemaVersion!=1||s.Source!="fastly-hosts-adjust"||s.Evidence!="latency_only"||s.SafeToApply||s.Candidates==nil||s.ScannedBlocks<0||s.SkippedBlocks<0{return errors.New("untrusted scan")}
 for _,c:=range s.Candidates {
   if c.Service!="github"&&c.Service!="x"&&c.Service!="twitch"{return errors.New("unapproved service")}
   ip:=net.ParseIP(c.IP)
   if ip==nil||ip.To4()==nil||ip.IsLoopback()||ip.IsPrivate()||ip.IsUnspecified()||ip.IsMulticast()||ip.IsLinkLocalUnicast(){return errors.New("invalid candidate IP")}
   if c.Pop==""||c.LatencyMS<=0{return errors.New("invalid candidate observation")}
 }
 return nil
}
// Run is offline-only: scan is externally supplied fixture evidence, not a network action.
// A successful scan updates only a caller-selected state file; all other outcomes preserve bytes.
func Run(config,old,scan []byte,now int64)(string,[]byte,error){
 c,err:=LoadConfig(config);if err!=nil{return "",nil,err}
 s,err:=LoadState(old);if err!=nil{return "",nil,err}
 if now<0{return "",nil,errors.New("invalid clock")}
 mode:=Mode(c,s,now)
 switch mode{
 case "skip":return "skipped",nil,nil
 case "benchmark_pending":return "pending",nil,nil
 case "health":
   if err:=ValidateScan(scan);err!=nil{return "error",nil,err}
   s.LastHealth=&now
   next,err:=json.Marshal(s);if err!=nil{return "error",nil,err}
   return "ok",append(next,'\n'),nil
 }
 return "",nil,errors.New("unknown mode")
}
func RunFiles(configPath,statePath,scanPath string,now int64)(string,error){
 c,err:=os.ReadFile(configPath);if err!=nil{return "",err}
 s,err:=os.ReadFile(statePath);if os.IsNotExist(err){s=nil}else if err!=nil{return "",err}
 scan,err:=os.ReadFile(scanPath);if os.IsNotExist(err){scan=nil}else if err!=nil{return "",err}
 result,next,err:=Run(c,s,scan,now);if err!=nil{return result,err}
 if next==nil{return result,nil}
 dir:=filepath.Dir(statePath)
 tmp,err:=os.CreateTemp(dir,".fastly-state-*");if err!=nil{return "error",err}
 name:=tmp.Name();defer os.Remove(name)
 if _,err=tmp.Write(next);err!=nil{tmp.Close();return "error",err}
 if err=tmp.Sync();err!=nil{tmp.Close();return "error",err}
 if err=tmp.Close();err!=nil{return "error",err}
 if err=os.Rename(name,statePath);err!=nil{return "error",err}
 return result,nil
}
