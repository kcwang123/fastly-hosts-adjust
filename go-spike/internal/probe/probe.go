package probe

import (
 "context"
 "crypto/tls"
 "crypto/x509"
 "errors"
 "fmt"
 "io"
 "net"
 "net/http"
 "strconv"
 "strings"
 "time"

 "github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/scanner"
)

var paths = map[string]string{
 "raw.githubusercontent.com": "/github/gitignore/main/README.md",
 "pbs.twimg.com": "/profile_images/1683325380441128960/yRsRRjGO_400x400.jpg",
 "static-cdn.jtvnw.net": "/jtv_user_pictures/xarth/404_user_70x70.png",
}
type Result struct {
 SchemaVersion int `json:"schema_version"`
 Domain string `json:"domain"`
 IP string `json:"ip"`
 TLSVerified bool `json:"tls_verified"`
 Status int `json:"http_status"`
 Bytes int64 `json:"bytes"`
 ContentRange string `json:"content_range"`
 ETag string `json:"etag"`
 CacheState string `json:"cache_state"`
 SafeToApply bool `json:"safe_to_apply"`
}
// ValidateResponse is transport-independent and rejects incomplete or oversized 206 data.
func ValidateResponse(r *http.Response, n int64)(Result,error){
 if n<=0||n>1<<20{return Result{},errors.New("invalid limit")}
 if r.StatusCode!=206{return Result{},errors.New("not partial content")}
 ce:=r.Header.Get("Content-Encoding");if ce!=""&&!strings.EqualFold(ce,"identity"){return Result{},errors.New("compressed")}
 prefix:=fmt.Sprintf("bytes 0-%d/",n-1)
 cr:=r.Header.Get("Content-Range")
 if !strings.HasPrefix(cr,prefix){return Result{},errors.New("wrong content range")}
 total:=strings.TrimPrefix(cr,prefix)
 if total!="*"{x,e:=strconv.ParseInt(total,10,64);if e!=nil||x<n{return Result{},errors.New("invalid object size")}}
 if r.ContentLength>=0&&r.ContentLength!=n{return Result{},errors.New("length mismatch")}
 if strings.Contains(strings.ToLower(r.Header.Get("Cache-Control")),"no-store"){return Result{},errors.New("no-store")}
 read,e:=io.CopyN(io.Discard,r.Body,n)
 if e!=nil||read!=n{return Result{},errors.New("truncated")}
 one:=make([]byte,1);extra,ee:=r.Body.Read(one)
 if extra!=0||ee!=io.EOF{return Result{},errors.New("oversized or unfinished response")}
 cache:=strings.ToUpper(r.Header.Get("X-Cache"));if cache!="HIT"&&cache!="MISS"{cache="UNKNOWN"}
 return Result{SchemaVersion:1,TLSVerified:true,Status:206,Bytes:read,ContentRange:cr,ETag:r.Header.Get("ETag"),CacheState:cache,SafeToApply:false},nil
}
// Range can only be called by Go tests/library code; the CLI has no network command.
// Injected dial permits fully local TLS testing without outbound public requests.
func Range(ctx context.Context,domain,ip string,n int64,roots *x509.CertPool,dial func(context.Context,string,string)(net.Conn,error))(Result,error){
 path,ok:=paths[domain];if !ok{return Result{},errors.New("unapproved host")}
 if !scanner.PublicIPv4(ip){return Result{},errors.New("nonpublic IPv4")}
 if n<=0||n>1<<20{return Result{},errors.New("budget")}
 if dial==nil{dial=(&net.Dialer{Timeout:3*time.Second}).DialContext}
 tr:=&http.Transport{Proxy:nil,DisableKeepAlives:true,DisableCompression:true,
   TLSClientConfig:&tls.Config{MinVersion:tls.VersionTLS12,ServerName:domain,RootCAs:roots},
   DialContext:func(ctx context.Context,network,_ string)(net.Conn,error){return dial(ctx,network,net.JoinHostPort(ip,"443"))}}
 defer tr.CloseIdleConnections()
 c:=&http.Client{Transport:tr,Timeout:5*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return errors.New("redirect denied")}}
 req,e:=http.NewRequestWithContext(ctx,"GET","https://"+domain+path,nil);if e!=nil{return Result{},e}
 req.Header.Set("Range",fmt.Sprintf("bytes=0-%d",n-1));req.Header.Set("Accept-Encoding","identity")
 resp,e:=c.Do(req);if e!=nil{return Result{},e};defer resp.Body.Close()
 out,e:=ValidateResponse(resp,n);if e!=nil{return Result{},e}
 out.Domain=domain;out.IP=ip
 return out,nil
}
