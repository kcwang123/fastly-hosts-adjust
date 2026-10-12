package probe

import (
 "context"
 "crypto/ecdsa"
 "crypto/elliptic"
 "crypto/rand"
 "crypto/tls"
 "crypto/x509"
 "math/big"
 "fmt"
 "net"
 "net/http"
 "net/http/httptest"
 "testing"
 "time"
)
func TestRangeContract(t *testing.T){
 for _,tc:=range []struct{name string;status int;cr,body string;fail bool}{
 {"pass",206,"bytes 0-3/100","test",false},
 {"range_ignored",200,"bytes 0-3/100","test",true},
 {"wrong_range",206,"bytes 1-4/100","test",true},
 {"truncated",206,"bytes 0-3/100","te",true},
 {"oversized",206,"bytes 0-3/100","tests",true},
 } {
 t.Run(tc.name,func(t *testing.T){
  ts:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){w.Header().Set("Content-Range",tc.cr);w.WriteHeader(tc.status);fmt.Fprint(w,tc.body)}));defer ts.Close()
  resp,e:=http.Get(ts.URL);if e!=nil{t.Fatal(e)};defer resp.Body.Close()
  _,e=ValidateResponse(resp,4);if (e!=nil)!=tc.fail{t.Fatalf("err %v expected fail %v",e,tc.fail)}
 })
 }
}
func TestTLSPositiveAndNegative(t *testing.T){
 key,e:=ecdsa.GenerateKey(elliptic.P256(),rand.Reader);if e!=nil{t.Fatal(e)}
 template:=&x509.Certificate{SerialNumber:big.NewInt(1),DNSNames:[]string{"raw.githubusercontent.com"},NotBefore:time.Now().Add(-time.Hour),NotAfter:time.Now().Add(time.Hour),KeyUsage:x509.KeyUsageDigitalSignature,ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
 der,e:=x509.CreateCertificate(rand.Reader,template,template,&key.PublicKey,key);if e!=nil{t.Fatal(e)}
 cert,e:=x509.ParseCertificate(der);if e!=nil{t.Fatal(e)}
 ts:=httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
 if r.Host!="raw.githubusercontent.com"||r.Header.Get("Range")!="bytes=0-3"{t.Errorf("request contract mismatch")}
 w.Header().Set("Content-Range","bytes 0-3/100");w.Header().Set("Content-Length","4");w.Header().Set("ETag",`"v1"`);w.Header().Set("X-Cache","HIT");w.WriteHeader(206);fmt.Fprint(w,"test")
 }))
 ts.TLS=&tls.Config{Certificates:[]tls.Certificate{{Certificate:[][]byte{der},PrivateKey:key}}};ts.StartTLS();defer ts.Close()
 roots:=x509.NewCertPool();roots.AddCert(cert)
 dial:=func(_ context.Context,_,_ string)(net.Conn,error){return net.Dial("tcp",ts.Listener.Addr().String())}
 out,e:=Range(context.Background(),"raw.githubusercontent.com","8.8.8.8",4,roots,dial)
 if e!=nil{t.Fatal(e)}
 if !out.TLSVerified||out.Bytes!=4||out.Status!=206||out.SafeToApply||out.ETag!=`"v1"`{t.Fatalf("unexpected %+v",out)}
 if _,e=Range(context.Background(),"pbs.twimg.com","8.8.8.8",4,roots,dial);e==nil{t.Fatal("hostname mismatch accepted")}
}
func TestRejectTargets(t *testing.T){
 for _,ip:=range []string{"127.0.0.1","192.168.1.1","::1","bad"}{
 if _,e:=Range(context.Background(),"raw.githubusercontent.com",ip,4,nil,nil);e==nil{t.Fatalf("accepted %s",ip)}
 }
 if _,e:=Range(context.Background(),"invalid.example","8.8.8.8",4,nil,nil);e==nil{t.Fatal("accepted unapproved host")}
}
