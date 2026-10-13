// fastly-decision is an offline-only advisory tool. It never initiates network traffic.
package main

import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"

 "github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/decision"
 "github.com/kcwang123/fastly-hosts-adjust/go-spike/internal/strictjson"
)

type request struct {
 SchemaVersion int `json:"schema_version"`
 Baseline decision.Sample `json:"baseline"`
 Candidates []decision.Sample `json:"candidates"`
}

func evaluate(data []byte)(decision.Recommendation,error){
 var input request
 if err:=strictjson.Decode(data,&input);err!=nil{return decision.Recommendation{},err}
 if input.SchemaVersion!=1{return decision.Recommendation{},errors.New("unsupported schema_version")}
 if input.Candidates==nil{return decision.Recommendation{},errors.New("candidates required")}
 return decision.Evaluate(input.Baseline,input.Candidates)
}
func main(){
 filename:=flag.String("input","","local JSON evidence file")
 flag.Parse()
 if *filename==""||flag.NArg()!=0 {fmt.Fprintln(os.Stderr,"--input required, no positional arguments");os.Exit(2)}
 // This binary has no sockets or router writers. Strict decoding imposes a 1MiB cap.
 data,err:=os.ReadFile(*filename)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 out,err:=evaluate(data)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(out);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
