package main

import "testing"

func TestValidateRejectsUnsafeInput(t *testing.T) {
 cases:=[]struct{name,service,ip string; bytes int64;ack bool}{
  {"missing opt-in","github","199.232.160.133",4096,false},
  {"unapproved service","notion","199.232.160.133",4096,true},
  {"loopback","github","127.0.0.1",4096,true},
  {"private","github","192.168.1.1",4096,true},
  {"IPv6","github","::1",4096,true},
  {"empty","github","",4096,true},
  {"zero bytes","github","199.232.160.133",0,true},
  {"oversized","github","199.232.160.133",65537,true},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  if _,err:=validate(tc.service,tc.ip,tc.bytes,tc.ack);err==nil{t.Fatal("unsafe input accepted")}
 })}
}

func TestValidateAllowsBoundedServiceCandidates(t *testing.T) {
 for _,svc:=range []string{"github","x","twitch"}{
  domain,err:=validate(svc,"199.232.160.133",4096,true)
  if err!=nil||domain==""{t.Fatalf("%s: domain=%q err=%v",svc,domain,err)}
 }
}

func TestRejectedInputNeverTouchesNetwork(t *testing.T){
 r,err:=run("github","127.0.0.1",4096,true)
 if err==nil||r.NetworkExecuted||r.SafeToApply||r.Result!=nil{t.Fatalf("unsafe report: %+v err=%v",r,err)}
}
