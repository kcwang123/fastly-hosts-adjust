package strictjson
import("bytes";"encoding/json";"errors";"fmt";"io")
const MaxBytes=1<<20
func Decode(data []byte,out any)error{
 if len(data)==0||len(data)>MaxBytes{return errors.New("JSON size outside limit")}
 d:=json.NewDecoder(bytes.NewReader(data))
 if err:=check(d,0);err!=nil{return err}
 if _,err:=d.Token();err!=io.EOF{return errors.New("trailing JSON")}
 d=json.NewDecoder(bytes.NewReader(data));d.DisallowUnknownFields()
 if err:=d.Decode(out);err!=nil{return err}
 if _,err:=d.Token();err!=io.EOF{return errors.New("trailing JSON")}
 return nil
}
func check(d *json.Decoder,depth int)error{
 if depth>16{return errors.New("JSON nesting limit")}
 t,err:=d.Token();if err!=nil{return err}
 sep,ok:=t.(json.Delim);if !ok{return nil}
 switch sep{
 case '{':
  seen:=map[string]bool{}
  for d.More(){key,err:=d.Token();if err!=nil{return err};s,ok:=key.(string);if !ok{return errors.New("invalid object key")};if seen[s]{return fmt.Errorf("duplicate JSON key: %s",s)};seen[s]=true
   if err:=check(d,depth+1);err!=nil{return err}
  }
 case '[':
  for d.More(){if err:=check(d,depth+1);err!=nil{return err}}
 default:return errors.New("unexpected delimiter")
 }
 _,err=d.Token();return err
}
