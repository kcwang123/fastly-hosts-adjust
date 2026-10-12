// A deliberately offline-only read-only contract spike. No network or router writes.
package main
import ("encoding/json";"errors";"flag";"fmt";"os")
type settings struct { DryRun bool `json:"dry_run"`; AutoBenchmark bool `json:"auto_benchmark"` }
func validate(b []byte) error {
 var m map[string]json.RawMessage
 if err:=json.Unmarshal(b,&m);err!=nil{return err}
 if len(m)!=2{return errors.New("two safety gates required")}
 for k:=range m {if k!="dry_run"&&k!="auto_benchmark"{return fmt.Errorf("unsupported setting: %s",k)}}
 var s settings;if err:=json.Unmarshal(b,&s);err!=nil{return err}
 if !s.DryRun||s.AutoBenchmark{return errors.New("read-only safety gates violated")}
 return nil
}
func main(){
 path:=flag.String("config","","minimal safety-gate JSON");flag.Parse()
 if *path==""{fmt.Fprintln(os.Stderr,"--config required");os.Exit(2)}
 b,err:=os.ReadFile(*path);if err==nil{err=validate(b)}
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 fmt.Println(`{"schema_version":1,"status":"validated_only","safe_to_apply":false,"network_executed":false}`)
}
