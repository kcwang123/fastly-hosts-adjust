package scanner
import "testing"
func TestConservativePublicIPv4(t *testing.T){
 for _,tc:=range []struct{ip string;ok bool}{
 {"8.8.8.8",true},{"1.1.1.1",true},{"100.64.0.1",false},
 {"192.0.2.1",false},{"198.19.1.1",false},{"203.0.113.8",false},
 {"192.0.0.8",false},{"240.0.0.1",false},{"255.255.255.255",false},
 {"0.1.2.3",false},{"169.254.1.2",false},{"127.0.0.1",false},
 {"::ffff:8.8.8.8",false},{"2001:db8::1",false},
 }{if actual:=PublicIPv4(tc.ip);actual!=tc.ok{t.Errorf("%s got %v want %v",tc.ip,actual,tc.ok)}}
}
