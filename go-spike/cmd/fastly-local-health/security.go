package main

import (
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "syscall"
)

// This is a CI harness file boundary, not a router deployment policy.
func safeFile(path string,optional bool)error{
 info,err:=os.Lstat(path)
 if os.IsNotExist(err)&&optional{return nil}
 if err!=nil{return err}
 if !info.Mode().IsRegular(){return fmt.Errorf("non-regular or symlink file: %s",path)}
 if info.Mode().Perm()&0077!=0{return fmt.Errorf("file accessible to group/other: %s",path)}
 stat,ok:=info.Sys().(*syscall.Stat_t)
 if !ok||int(stat.Uid)!=os.Geteuid(){return errors.New("file owner mismatch")}
 return nil
}
func lockedState(path string,fn func()(string,error))(string,error){
 dir:=filepath.Dir(path)
 info,err:=os.Lstat(dir);if err!=nil{return "",err}
 if !info.IsDir()||info.Mode().Perm()&0022!=0{return "",errors.New("unsafe state directory")}
 // O_NOFOLLOW rejects an attacker-supplied lock symlink.
 fd,err:=syscall.Open(path+".lock",syscall.O_CREAT|syscall.O_RDWR|syscall.O_NOFOLLOW|syscall.O_CLOEXEC,0600)
 if err!=nil{return "",err}
 defer syscall.Close(fd)
 if err:=safeFile(path+".lock",false);err!=nil{return "",err}
 if err:=syscall.Flock(fd,syscall.LOCK_EX);err!=nil{return "",err}
 defer syscall.Flock(fd,syscall.LOCK_UN)
 return fn()
}
