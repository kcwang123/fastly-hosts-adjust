package scheduler
import (
 "context"
 "errors"
 "testing"
 "time"
 "github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/scanner"
)
func TestInjectedHealthFailClosed(t *testing.T){
 targets:=[]scanner.Target{{Service:"github",IP:"8.8.8.8"}}
 good:=func(ctx context.Context,h,ip string)(string,time.Duration,error){return "UNKNOWN",15*time.Millisecond,nil}
 bad:=func(ctx context.Context,h,ip string)(string,time.Duration,error){return "",0,errors.New("fault")}
 result,next,scan,err:=RunHealth(context.Background(),config,nil,100000,targets,good)
 if err!=nil||result!="ok"||next==nil||scan==nil{t.Fatalf("expected health success: %s %v",result,err)}
 if err=ValidateScan(scan);err!=nil{t.Fatal(err)}
 result,next,scan,err=RunHealth(context.Background(),config,nil,100000,targets,bad)
 if result!="error"||err==nil||next!=nil||scan!=nil{t.Fatal("failed scan changed state")}
 state:=[]byte(`{"last_health_epoch":100000,"last_benchmark_epoch":100000}`)
 result,next,scan,err=RunHealth(context.Background(),config,state,100001,targets,bad)
 if result!="skipped"||err!=nil||next!=nil||scan!=nil{t.Fatal("skip should not run scanner")}
}
