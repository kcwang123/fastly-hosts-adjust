package strictjson
import "testing"
func TestRejectDuplicatesAndTrailing(t *testing.T){
 for _,raw:=range []string{
  `{"a":1,"a":2}`,`{"a":{"b":1,"b":2}}`,`[{"x":1,"x":2}]`,
  `{"a":1} true`,`{"a":1,"nested":[{"x":3,"x":4}]}`,
 }{var v any;if err:=Decode([]byte(raw),&v);err==nil{t.Fatalf("accepted %s",raw)}}
 var valid any;if err:=Decode([]byte(`{"a":[{"b":2}]}`),&valid);err!=nil{t.Fatal(err)}
}
