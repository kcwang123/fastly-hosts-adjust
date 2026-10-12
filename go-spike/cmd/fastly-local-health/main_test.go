package main
import(
 "crypto/ecdsa"
 "crypto/elliptic"
 "crypto/rand"
 "crypto/tls"
 "crypto/x509"
 "encoding/pem"
 "math/big"
 "net/http"
 "net/http/httptest"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"
)
func TestLocalHealthCLI(t *testing.T){
 dir:=t.TempDir()
 key,e:=ecdsa.GenerateKey(elliptic.P256(),rand.Reader);if e!=nil{t.Fatal(e)}
 cert:=&x509.Certificate{SerialNumber:big.NewInt(7),DNSNames:[]string{"raw.githubusercontent.com"},NotBefore:time.Now().Add(-time.Hour),NotAfter:time.Now().Add(time.Hour),KeyUsage:x509.KeyUsageDigitalSignature,ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
 der,e:=x509.CreateCertificate(rand.Reader,cert,cert,&key.PublicKey,key);if e!=nil{t.Fatal(e)}
 srv:=httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){if r.URL.Path!="/github/gitignore/main/README.md"{t.Error("unexpected path")};w.WriteHeader(200)}))
 srv.TLS=&tls.Config{Certificates:[]tls.Certificate{{Certificate:[][]byte{der},PrivateKey:key}}};srv.StartTLS();defer srv.Close()
 cp:=filepath.Join(dir,"config");sp:=filepath.Join(dir,"state");tp:=filepath.Join(dir,"targets");ca:=filepath.Join(dir,"ca.pem")
 os.WriteFile(cp,[]byte(`{"dry_run":true,"auto_benchmark":false}`),0600)
 os.WriteFile(tp,[]byte(`[{"service":"github","ip":"8.8.8.8"}]`),0600)
 os.WriteFile(ca,pem.EncodeToMemory(&pem.Block{Type:"CERTIFICATE",Bytes:der}),0600)
 result,e:=run(cp,sp,tp,ca,srv.Listener.Addr().String(),10000)
 if e!=nil||result!="ok"{t.Fatalf("local TLS scan: %s %v",result,e)}
 state,e:=os.ReadFile(sp);if e!=nil||!strings.Contains(string(state),"last_health_epoch"){t.Fatalf("state: %q %v",state,e)}
 previous:=append([]byte(nil),state...)
 os.WriteFile(tp,[]byte(`[{"service":"x","ip":"8.8.8.8"}]`),0600)
 if _,e=run(cp,sp,tp,ca,srv.Listener.Addr().String(),30000);e==nil{t.Fatal("wrong hostname passed")}
 after,_:=os.ReadFile(sp);if string(after)!=string(previous){t.Fatal("failed TLS changed state")}
 if _,e=run(cp,sp,tp,ca,"8.8.8.8:443",30000);e==nil{t.Fatal("public listener accepted")}
}
func TestStrictTargetFile(t *testing.T){
 for _,s:=range []string{`[{"service":"github","ip":"8.8.8.8","extra":1}]`,`[]`,`[{"service":"github"}]`,`[{"service":"github","ip":"8.8.8.8"}] true`}{
  if _,e:=loadTargets([]byte(s));e==nil{t.Fatalf("accepted bad target %s",s)}
 }
}
