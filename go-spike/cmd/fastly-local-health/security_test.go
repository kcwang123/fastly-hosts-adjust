package main
import("os";"path/filepath";"sync";"testing")
func TestUnsafeFilesRejected(t *testing.T){
 dir:=t.TempDir()
 file:=filepath.Join(dir,"fixture");if err:=os.WriteFile(file,[]byte("x"),0600);err!=nil{t.Fatal(err)}
 if err:=safeFile(file,false);err!=nil{t.Fatal(err)}
 alias:=filepath.Join(dir,"alias");if err:=os.Symlink(file,alias);err!=nil{t.Fatal(err)}
 if err:=safeFile(alias,false);err==nil{t.Fatal("accepted symlink")}
 if err:=os.Chmod(file,0644);err!=nil{t.Fatal(err)}
 if err:=safeFile(file,false);err==nil{t.Fatal("accepted unsafe permissions")}
}
func TestStateLockSerializes(t *testing.T){
 path:=filepath.Join(t.TempDir(),"state")
 count:=0;var wg sync.WaitGroup
 for i:=0;i<4;i++{wg.Add(1);go func(){defer wg.Done();_,err:=lockedState(path,func()(string,error){value:=count;count=value+1;return "ok",nil});if err!=nil{t.Error(err)}}()}
 wg.Wait()
 if count!=4{t.Fatalf("lost serialized updates: %d",count)}
}

func TestStateLockRejectsUntrustedDirectory(t *testing.T){
 dir:=t.TempDir()
 path:=filepath.Join(dir,"state")
 if err:=os.Chmod(dir,0777);err!=nil{t.Fatal(err)}
 if _,err:=lockedState(path,func()(string,error){return "unexpected",nil});err==nil{t.Fatal("world-writable parent accepted")}
 if err:=os.Chmod(dir,0700);err!=nil{t.Fatal(err)}
 alias:=path+".lock"
 if err:=os.Symlink(filepath.Join(dir,"target"),alias);err!=nil{t.Fatal(err)}
 if _,err:=lockedState(path,func()(string,error){return "unexpected",nil});err==nil{t.Fatal("lock symlink accepted")}
}
