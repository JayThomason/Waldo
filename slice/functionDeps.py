#!/usr/bin/env python


class FunctionDeps(object):

    def __init__(self,funcName):
        # name to an array of NameTypeTuple-s
        # each variable in here may be dependent on the list
        # NameTypeTuple-s
        self.varReadSet = {}; 

        # the variables that this function reads from. dict from var
        # name to NameTypeTuple.
        self.mReadSet = {}; 

        # the variables that this function writes to
        self.mWriteSet = {};

        self.funcName = funcName;
        
    def addToVarReadSet(self,nodeName,nameTypeTuple):
        if self.varReadSet.get(nodeName,None) == None:
            self.varReadSet[nodeName] = VarReadSet(nameTypeTuple);
        else:
            print('\nBehram error.  Should not permit redeclaration.\n');
            assert(False);
            
    def addReadsWritesToVarReadSet(self,nodeName,reads,writes):
        if self.varReadSet.get(nodeName,None) == None:
            print('\nBehram error.  Should not permit redeclaration.\n');
            assert(False);
        else:
            self.varReadSet[nodeName].addReads(reads);
            self.varReadSet[nodeName].addWrites(writes);
            
        self.addFuncReadsWrites(reads,writes);
            
    def addFuncReadsWrites(self,reads,writes):
        for read in reads:
            self.mReadSet[read.varName] = read;

        for write in writes:
            self.mWriteSet[write.varName] = write;

    def _debugPrint(self):
        print('\n');
        print(self.funcName);
        for item in self.mReadSet.keys():
            print(item);
        for item in self.mWriteSet.keys():
            print(item);


class VarReadSet(object):
    def __init__(self,ntt):
        self.ntt = ntt;
        self.mReads = {};
        # note: this should never really be populated because there
        # are not ways to return and modify....except through func call
        # actually.
        self.mWrites = {};
        
    def addReads(self,reads):
        for read in reads:
            self.mReads[read.varName] = read;

    def addWrites(self,writes):
        for write in writes:
            self.mWrites[write.varName] = write;