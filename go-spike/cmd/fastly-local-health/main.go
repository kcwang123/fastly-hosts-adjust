// fastly-local-health is a CI-only localhost TLS harness, not a router runtime.
// All sockets are physically dialed to loopback. It never probes configured public IPs.
package main
import(
 "bytes"
 "context"
 "crypto/x509"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "net"
 "os"
 "path/filepath"
 "time"
 "github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/scanner"
 "github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/scheduler"
)
func loadTargets(b []byte)([]scanner.Target,error){
 d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 var t []scanner.Target
 if err:=d.Decode(&t);err!=nil{return nil,err}
 var leftover any
 if err:=d.Decode(&leftover);err!=io.EOF{return nil,errors.New("trailing targets JSON")}
 if len(t)==0||len(t)>20{return nil,errors.New("target count outside 1..20")}
 for _,x:=range t{if x.Service==""||x.IP==""{return nil,errors.New("incomplete target")}}
 return t,nil
}
func run(config,state,targets,ca,addr string,now int64)(string,error){
 host,_,err:=net.SplitHostPort(addr);if err!=nil{return "",err}
 parsed:=net.ParseIP(host)
 if parsed==nil||!parsed.IsLoopback(){return "",errors.New("only numeric loopback TLS listener permitted")}
 if now<=0{return "",errors.New("explicit epoch required")}
 cf,err:=os.ReadFile(config);if err!=nil{return "",err}
 old,err:=os.ReadFile(state);if os.IsNotExist(err){old=nil}else if err!=nil{return "",err}
 raw,err:=os.ReadFile(targets);if err!=nil{return "",err}
 list,err:=loadTargets(raw);if err!=nil{return "",err}
 pem,err:=os.ReadFile(ca);if err!=nil{return "",err}
 roots:=x509.NewCertPool();if !roots.AppendCertsFromPEM(pem){return "",errors.New("invalid test CA")}
 dial:=func(ctx context.Context,_,_ string)(net.Conn,error){
  return (&net.Dialer{Timeout:3*time.Second}).DialContext(ctx,"tcp",addr)
 }
 ctx,cancel:=context.WithTimeout(context.Background(),10*time.Second);defer cancel()
 status,next,_,err:=scheduler.RunHealth(ctx,cf,old,now,list,scanner.TLSHeadProbe(roots,dial))
 if err!=nil{return status,err}
 if next==nil{return status,nil}
 tmp,err:=os.CreateTemp(filepath.Dir(state),".fastly-local-*");if err!=nil{return "",err}
 name:=tmp.Name();defer os.Remove(name)
 if _,err=tmp.Write(next);err!=nil{tmp.Close();return "",err}
 if err=tmp.Sync();err!=nil{tmp.Close();return "",err}
 if err=tmp.Close();err!=nil{return "",err}
 if err=os.Rename(name,state);err!=nil{return "",err}
 return status,nil
}
func main(){
 config:=flag.String("config","","read-only safety settings")
 state:=flag.String("state","","test state file")
 targets:=flag.String("targets","","bounded public-IP labels (no public connections)")
 ca:=flag.String("test-ca","","localhost test CA PEM")
 addr:=flag.String("loopback-tls","","numeric 127.0.0.1 or ::1 TLS listener")
 now:=flag.Int64("now",0,"explicit epoch")
 flag.Parse()
 if *config==""||*state==""||*targets==""||*ca==""||*addr==""{fmt.Fprintln(os.Stderr,"all flags required");os.Exit(2)}
 status,err:=run(*config,*state,*targets,*ca,*addr,*now)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 fmt.Printf("{\"status\":%q,\"safe_to_apply\":false,\"network_executed\":false,\"loopback_test_only\":true}\n",status)
}
