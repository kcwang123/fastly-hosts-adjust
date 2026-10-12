package scanner

import (
 "context"
 "crypto/tls"
 "crypto/x509"
 "errors"
 "fmt"
 "net"
 "net/http"
 "time"
)

// TLSHeadProbe validates pinned IP against the original hostname. No redirects
// and no proxy; dial must be explicitly injected by the caller.
func TLSHeadProbe(roots *x509.CertPool,dial func(context.Context,string,string)(net.Conn,error)) Probe {
 return func(ctx context.Context,host,ip string)(string,time.Duration,error){
  if dial==nil{return "",0,errors.New("dialer not configured")}
  start:=time.Now()
  tr:=&http.Transport{Proxy:nil,DisableKeepAlives:true,DisableCompression:true,
   TLSClientConfig:&tls.Config{MinVersion:tls.VersionTLS12,ServerName:host,RootCAs:roots},
   DialContext:func(c context.Context,network,_ string)(net.Conn,error){return dial(c,network,net.JoinHostPort(ip,"443"))}}
  defer tr.CloseIdleConnections()
  client:=&http.Client{Transport:tr,CheckRedirect:func(*http.Request,[]*http.Request)error{return errors.New("redirect denied")}}
  request,err:=http.NewRequestWithContext(ctx,http.MethodHead,"https://"+host+"/",nil)
  if err!=nil{return "",0,err}
  response,err:=client.Do(request)
  if err!=nil{return "",0,err}
  response.Body.Close()
  if response.StatusCode<200||response.StatusCode>=400{return "",0,fmt.Errorf("unhealthy status %d",response.StatusCode)}
  // POP is not attested by TLS; use only a diagnostic label, never route approval.
  return "UNKNOWN",time.Since(start),nil
 }
}
