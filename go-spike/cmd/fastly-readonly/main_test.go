package main
import "testing"
func TestGates(t *testing.T){
 for _,tc:=range []struct{json string;ok bool}{
 {`{"dry_run":true,"auto_benchmark":false}`,true},
 {`{"dry_run":false,"auto_benchmark":false}`,false},
 {`{"dry_run":true,"auto_benchmark":true}`,false},
 {`{"dry_run":true}`,false},
 {`{"dry_run":true,"auto_benchmark":false,"unexpected":1}`,false},
 }{if (validate([]byte(tc.json))==nil)!=tc.ok{t.Errorf("wrong validation: %s",tc.json)}}
}
