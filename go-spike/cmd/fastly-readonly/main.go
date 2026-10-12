// A deliberately offline-only read-only contract spike. No network or router writes.
package main
import ("encoding/json";"errors";"flag";"fmt";"os";"github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/scheduler";"github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/strictjson")
type settings struct { DryRun bool `json:"dry_run"`; AutoBenchmark bool `json:"auto_benchmark"` }
func validate(b []byte) error {
 var m map[string]json.RawMessage
 if err:=strictjson.Decode(b,&m);err!=nil{return err}
 if len(m)!=2{return errors.New("two safety gates required")}
 for k:=range m {if k!="dry_run"&&k!="auto_benchmark"{return fmt.Errorf("unsupported setting: %s",k)}}
 var s settings;if err:=strictjson.Decode(b,&s);err!=nil{return err}
 if !s.DryRun||s.AutoBenchmark{return errors.New("read-only safety gates violated")}
 return nil
}
func main(){
 path:=flag.String("config","","minimal safety-gate JSON")
 state:=flag.String("state","","offline scheduler state file")
 scan:=flag.String("scan-input","","offline scan JSON fixture (never collected via network)")
 now:=flag.Int64("now",0,"explicit epoch time for offline scheduler")
 flag.Parse()
 if *state!="" || *scan!="" {
   if *path=="" || *state=="" || *scan=="" || *now<=0 {fmt.Fprintln(os.Stderr,"offline scheduler requires --config, --state, --scan-input, --now");os.Exit(2)}
   mode,err:=scheduler.RunFiles(*path,*state,*scan,*now)
   if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
   fmt.Printf("{\"status\":%q,\"safe_to_apply\":false,\"network_executed\":false}\n",mode)
   return
 }
 if *path==""{fmt.Fprintln(os.Stderr,"--config required");os.Exit(2)}
 b,err:=os.ReadFile(*path);if err==nil{err=validate(b)}
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 fmt.Println(`{"schema_version":1,"status":"validated_only","safe_to_apply":false,"network_executed":false}`)
}
