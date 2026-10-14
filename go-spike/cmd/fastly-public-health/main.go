// fastly-public-health is an opt-in, bounded, read-only public HTTPS probe.
// This is NOT a CDN optimizer, Router installer, DNS writer or background daemon.
package main

import (
 "context"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "time"

 "github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/probe"
 "github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/scanner"
)

type report struct {
 SchemaVersion int `json:"schema_version"`
 Mode string `json:"mode"`
 NetworkExecuted bool `json:"network_executed"`
 SafeToApply bool `json:"safe_to_apply"`
 Service string `json:"service"`
 IP string `json:"ip"`
 StartedAt string `json:"started_at"`
 DurationMS int64 `json:"duration_ms"`
 Result *probe.Result `json:"result,omitempty"`
 Error string `json:"error,omitempty"`
}
var allowed=map[string]string{
 "github":"raw.githubusercontent.com",
 "x":"pbs.twimg.com",
 "twitch":"static-cdn.jtvnw.net",
}
func validate(service,ip string,n int64,ack bool) (string,error){
 if !ack {return "",errors.New("explicit --public-probe-required required")}
 domain,ok:=allowed[service];if !ok{return "",errors.New("unknown service")}
 if !scanner.PublicIPv4(ip){return "",errors.New("public IPv4 required")}
 if n<1||n>65536{return "",errors.New("byte budget must be 1..65536")}
 return domain,nil
}
func run(service,ip string,n int64,ack bool) (report,error) {
 start:=time.Now()
 r:=report{SchemaVersion:1,Mode:"read_only",SafeToApply:false,Service:service,IP:ip,StartedAt:start.UTC().Format(time.RFC3339)}
 domain,err:=validate(service,ip,n,ack)
 if err!=nil {r.Error=err.Error();return r,err}
 ctx,cancel:=context.WithTimeout(context.Background(),7*time.Second);defer cancel()
 r.NetworkExecuted=true
 result,err:=probe.Range(ctx,domain,ip,n,nil,nil)
 r.DurationMS=time.Since(start).Milliseconds()
 if err!=nil{r.Error=err.Error();return r,err}
 r.Result=&result
 return r,nil
}
func main(){
 service:=flag.String("service","","github|x|twitch")
 ip:=flag.String("ip","","explicit IPv4 candidate (no DNS modification)")
 n:=flag.Int64("bytes",4096,"maximum response bytes, 1..65536")
 ack:=flag.Bool("public-probe-required",false,"explicit opt-in for a public-network request")
 flag.Parse()
 r,err:=run(*service,*ip,*n,*ack)
 // Never log credentials, response bodies or request headers.
 _=json.NewEncoder(os.Stdout).Encode(r)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
