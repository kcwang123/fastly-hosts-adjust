package scheduler
import ("os";"path/filepath";"bytes";"testing")
var config=[]byte(`{"dry_run":true,"auto_benchmark":false,"health_interval_hours":3,"benchmark_interval_hours":24}`)
var scan=[]byte(`{"schema_version":1,"evidence":"latency_only","safe_to_apply":false,"candidates":[]}`)
func TestModesAndSafety(t *testing.T){
 tests:=[]struct{name string;old,scan []byte;now int64;result string;write bool}{
 {"first",nil,scan,100000,"ok",true},
 {"skip",[]byte(`{"last_health_epoch":100000,"last_benchmark_epoch":100000}`),nil,100001,"skipped",false},
 {"benchmark pending",[]byte(`{"last_health_epoch":100000}`),nil,100001,"pending",false},
 {"missing scan",nil,nil,100000,"error",false},
 {"wrong scan",nil,[]byte(`{"schema_version":1,"evidence":"latency_only","safe_to_apply":true,"candidates":[]}`),100000,"error",false},
 {"bad state",[]byte(`{"last_health_epoch":-1}`),scan,100000,"",false},
 }
 for _,tc:=range tests{t.Run(tc.name,func(t *testing.T){
  result,data,err:=Run(config,tc.old,tc.scan,tc.now)
  if result!=tc.result||(data!=nil)!=tc.write{t.Fatalf("result %s write %v err %v",result,data!=nil,err)}
  if tc.result=="error"||tc.result==""{if err==nil{t.Fatal("expected error")}}else if err!=nil{t.Fatal(err)}
 })}
 for _,c:=range [][]byte{[]byte(`{"dry_run":false,"auto_benchmark":false}`),[]byte(`{"dry_run":true,"auto_benchmark":true}`),[]byte(`{"dry_run":true}`),[]byte(`{"dry_run":true,"auto_benchmark":false,"unexpected":3}`),[]byte(`{"dry_run":true,"auto_benchmark":false,"health_interval_hours":-1}`)}{if _,e:=LoadConfig(c);e==nil{t.Fatalf("unsafe config accepted: %s",c)}}
}
func TestStateOnlyChangesAfterVerifiedScan(t *testing.T){
 dir:=t.TempDir();cp:=filepath.Join(dir,"config.json");sp:=filepath.Join(dir,"state.json");xp:=filepath.Join(dir,"scan.json")
 if err:=os.WriteFile(cp,config,0600);err!=nil{t.Fatal(err)}
 before:=[]byte(`{"last_health_epoch":1}`);os.WriteFile(sp,before,0600)
 os.WriteFile(xp,[]byte(`{"schema_version":1,"evidence":"latency_only","safe_to_apply":true,"candidates":[]}`),0600)
 if _,err:=RunFiles(cp,sp,xp,20000);err==nil{t.Fatal("unsafe fixture accepted")}
 got,_:=os.ReadFile(sp);if !bytes.Equal(got,before){t.Fatal("state changed after failure")}
 os.WriteFile(xp,scan,0600)
 if mode,err:=RunFiles(cp,sp,xp,20000);mode!="ok"||err!=nil{t.Fatalf("mode %s err %v",mode,err)}
 got,_=os.ReadFile(sp);if bytes.Equal(got,before){t.Fatal("successful scan did not update state")}
}
