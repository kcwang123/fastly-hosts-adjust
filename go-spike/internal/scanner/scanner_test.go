package scanner

import (
 "context"
 "crypto/ecdsa"
 "crypto/elliptic"
 "crypto/rand"
 "crypto/tls"
 "crypto/x509"
 "encoding/json"
 "errors"
 "math/big"
 "net"
 "net/http"
 "net/http/httptest"
 "testing"
 "time"
)
func TestScannerBoundaries(t *testing.T){
 success:=func(_ context.Context,_,_ string)(string,time.Duration,error){return "UNKNOWN",time.Millisecond,nil}
 invalid:=[][]Target{{},{ {Service:"nope",IP:"8.8.8.8"} },{{Service:"github",IP:"127.0.0.1"}}}
 for _,ts:=range invalid{if _,err:=Scan(context.Background(),ts,success);err==nil{t.Fatalf("accepted %v",ts)}}
 evidence,err:=Scan(context.Background(),[]Target{{Service:"github",IP:"8.8.8.8"}},success);if err!=nil{t.Fatal(err)}
 var out Output;if err=json.Unmarshal(evidence,&out);err!=nil{t.Fatal(err)}
 if out.SafeToApply||out.Evidence!="latency_only"||len(out.Candidates)!=1{t.Fatalf("bad scan %+v",out)}
 fault:=func(_ context.Context,_,_ string)(string,time.Duration,error){return "",0,errors.New("io failure")}
 if _,err:=Scan(context.Background(),[]Target{{Service:"github",IP:"8.8.8.8"}},fault);err==nil{t.Fatal("failed open")}
 ctx,cancel:=context.WithCancel(context.Background());cancel()
 if _,err:=Scan(ctx,[]Target{{Service:"github",IP:"8.8.8.8"}},success);err==nil{t.Fatal("canceled context accepted")}
}
func TestBoundedRetries(t *testing.T){
 attempts:=0
 flaky:=func(_ context.Context,_,_ string)(string,time.Duration,error){
  attempts++
  if attempts<3{return "",0,errors.New("temporary failure")}
  return "UNKNOWN",time.Millisecond,nil
 }
 targets:=[]Target{{Service:"github",IP:"8.8.8.8"}}
 if _,err:=ScanWithRetries(context.Background(),targets,flaky,2);err!=nil||attempts!=3{t.Fatalf("retry failure: %d %v",attempts,err)}
 attempts=0
 if _,err:=ScanWithRetries(context.Background(),targets,flaky,1);err==nil||attempts!=2{t.Fatalf("retry limit ignored: %d %v",attempts,err)}
}
func TestInjectedTLSHead(t *testing.T){
 private,err:=ecdsa.GenerateKey(elliptic.P256(),rand.Reader);if err!=nil{t.Fatal(err)}
 template:=&x509.Certificate{SerialNumber:big.NewInt(42),DNSNames:[]string{"raw.githubusercontent.com"},NotBefore:time.Now().Add(-time.Hour),NotAfter:time.Now().Add(time.Hour),KeyUsage:x509.KeyUsageDigitalSignature,ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
 der,err:=x509.CreateCertificate(rand.Reader,template,template,&private.PublicKey,private);if err!=nil{t.Fatal(err)}
 cert,err:=x509.ParseCertificate(der);if err!=nil{t.Fatal(err)}
 server:=httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){w.WriteHeader(http.StatusOK)}))
 server.TLS=&tls.Config{Certificates:[]tls.Certificate{{Certificate:[][]byte{der},PrivateKey:private}}}
 server.StartTLS();defer server.Close()
 roots:=x509.NewCertPool();roots.AddCert(cert)
 dial:=func(_ context.Context,_,_ string)(net.Conn,error){return net.Dial("tcp",server.Listener.Addr().String())}
 health:=TLSHeadProbe(roots,dial)
 if _,err:=Scan(context.Background(),[]Target{{Service:"github",IP:"8.8.8.8"}},health);err!=nil{t.Fatal(err)}
 if _,err:=Scan(context.Background(),[]Target{{Service:"x",IP:"8.8.8.8"}},health);err==nil{t.Fatal("wrong SNI certificate accepted")}
}
