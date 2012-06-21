#!/usr/bin/python

import sys;
import os;
astParserPath = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..','parser','ast');
sys.path.insert(0, astParserPath);

from astBuilder_v1 import getParser as v1GetParser;
from astBuilder_v1 import getErrorEncountered as v1GetErrorEncountered;
from astBuilder_v1 import resetErrorEncountered as v1ResetErrorEncountered;


import canonicalize;
from astBuilder_v2 import getParser as v2GetParser;
from astBuilder_v2 import getErrorEncountered as v2GetErrorEncountered;
from astBuilder_v2 import resetErrorEncountered as v2ResetErrorEncountered;

def getParser(progText,outputErrsTo,versionNum):
    if versionNum == 1:
        return v1GetParser(progText,outputErrsTo);
    return v2GetParser(progText,outputErrsTo);

def getErrorEncountered(versionNum):
    if versionNum == 1:
        return v1GetErrorEncountered();
    return v2GetErrorEncountered();

def resetErrorEncountered(versionNum):
    if versionNum == 1:
        return v1ResetErrorEncountered();
    return v2ResetErrorEncountered();



import re;
from astNode import WaldoTypeCheckException;

import json;
astEmitPath = os.path.join(os.path.abspath(os.path.dirname(__file__)),'..','emitters','pyEmit');
sys.path.insert(0, astEmitPath);
import astEmit;

lexPath = os.path.join(os.path.abspath(os.path.dirname(__file__)),'..','lexer');
from waldoLex import WaldoLexException;


class GraphicalOutArg():
    def __init__(self,jsonDict):
        ##checks before hand if have file in dict, and if don't throws exception.
        self.outFile = jsonDict['file'];
        self.width = jsonDict.get('w',None);
        self.height = jsonDict.get('h',None);
        self.d3 = jsonDict.get('d3','../parser/ast/d3');


def getFileText(inputFile):
    filer = open(inputFile,'r');
    returner = '';
    for s in filer:
        returner += s;
    filer.close();
    returner = stripWindowsLineEndings(returner);
    return returner;

def stripWindowsLineEndings(textToStripFrom):
    return re.sub(r'\r','',textToStripFrom)

def runTests():
    print('Still to fill in');


def genAstFromFile(inputFilename,outputErrsTo,versionNum):
    fileText = getFileText(inputFilenameArg);
    return genAst(fileText,outputErrsTo,versionNum);


def astProduceTextOutput(astNode,textOutFilename):
    astNode.printAst(textOutFilename);
    return astNode;

def astProducePrintOutput(astNode):
    astNode.printAst();
    return astNode;

def astProduceGraphicalOutput(astNode,graphOutArg):
    '''
    @param graphOutArg is of type class GraphicalOutArg
    '''
    astNode.drawPretty(graphOutArg.outFile,graphOutArg.d3,graphOutArg.width,graphOutArg.height);
    return astNode;


def genAst(progText,outputErrsTo,versionNum):
    progText = stripWindowsLineEndings(progText);
    parser = getParser(progText,outputErrsTo,versionNum);
    astNode = parser.parse(progText);
    if (versionNum == 1):
        pass;
    elif(versionNum == 2):
        canonicalize.v2ToV1Ast(astNode,progText);
    else:
        print('\nError, no version information provided\n');
        assert(False);

    return astNode,progText;

def compileText(progText,outputErrStream,versionNum):
    '''
    Mostly will be used when embedding in another project.  
    
    @param {String} progText -- The source text that we are trying to
    compile.

    @param{File-like object} outputErrStream -- The stream that we should use to output
    error messages to.

    @param {Int} versionNum 1 or 2.
    
    @returns {String or None} -- if no errors were encountered,
    returns the compiled source of the file.  If compile errors were
    encountered, then returns None.
    '''


    try:
        astRootNode, other = genAst(progText,outputErrStream);
    except WaldoLexException as excep:
        print >> outputErrStream, excep.value;
        return None;
    except WaldoTypeCheckException as excep:
        print >> errOutputStream, excep.value;
        return;


    
    if (astRootNode == None):
        # means there was an error
        resetErrorEncountered(versionNum);
        return None;

    try:
        astRootNode.typeCheck(progText);
    except WaldoTypeCheckException as excep:
        resetErrorEncountered(versionNum);
        return None;

    
    if (getErrorEncountered(versionNum)):
        resetErrorEncountered(versionNum);

        
        # means there was a type error.  should not continue.
        return None;

    resetErrorEncountered(versionNum);
    emitText = astEmit.runEmitter(astRootNode,None,outputErrStream);
    return emitText; # will be none if encountered an error during
                     # emit.  otherwise, file text.


        
def handleArgs(inputFilename,graphicalOutputArg,textOutputArg,printOutputArg,typeCheckArg,emitArg,versionNum):
    errOutputStream = sys.stderr;


    try:
        ast,fileText = genAstFromFile(inputFilename,errOutputStream,versionNum);
    except WaldoLexException as excep:
        print >> errOutputStream, excep.value;
        return;
    except WaldoTypeCheckException as excep:
        print >> errOutputStream, excep.value;
        return;
    
    if (ast == None):
        print >> errOutputStream, '\nError with program.  Please fix and continue\n';
    else:
        performedOperation = False;
        if (textOutputArg != None):
            astProduceTextOutput(ast,textOutputArg);
            performedOperation = True;
        if (printOutputArg != None):
            astProducePrintOutput(ast);
            performedOperation = True;
        if(graphicalOutputArg != None):
            astProduceGraphicalOutput(ast,graphicalOutputArg);
            performedOperation = True;

        
        if(typeCheckArg):
            try:
                ast.typeCheck(fileText);
            except WaldoTypeCheckException as excep:
                pass;

            
        if (emitArg != None):
            
            if (getErrorEncountered(versionNum)):
                # do not emit any code if got a type error when tyring
                # to compile.
                errMsg = '\nType error: cancelling code emit\n';
                print >> errOutputStream, errMsg;
            else:
                emitText = astEmit.runEmitter(ast,None,errOutputStream);
                if (emitText == None):
                    errMsg = '\nBehram error when requesting emission of ';
                    errMsg += 'source code from astHead.py.\n';
                    print >> errOutputStream, errMsg;
                    assert(False);
                
                filer = open(emitArg,'w');
                filer.write(emitText);
                filer.flush();
                filer.close();






def parseGraphicalOutputArg(goJSON):
    '''
    @param {String} in form of JSON_OBJECT in printUsage.
    @throws exception if incorrectly formatted.
    @returns GraphicalOutArg object
    '''
    pyDict = json.loads(goJSON);

    if (pyDict.get('file',None) == None):
        printUsage();
        assert(False);

    return GraphicalOutArg(pyDict);



def printUsage():
    print(    '''
    -f <filename> input file to generate ast for.

    -go <JSON_OBJECT> (go = graphical output).

    JSON_OBJECT
    {
       file: <filename to output to>,
       d3: (optional) <path to d3 so output html can link to it>,
       h: (optional) <int> height of image to be drawn onto output html (default 1000),
       w: (optional) <int> width of image to be drawn onto output html (default 1000)

    }
    
    -tc  (optional) true/false whether to type check the function or not. defaults to True.

    -to <filename> spits printed json ast out. (text out)

    -p print the json ast directly to screen

    -h print options

    -e <filename> Emit the generated code to filename

    -v <version number 1 or 2> Input file is of version 1 or version 2.  Default is version 1

    no args ... run ast tests
    
    ''');



    
if __name__ == '__main__':

    inputFilenameArg = None;
    graphicalOutputArg = None;
    textOutputArg = None;
    helpArg = None;
    printOutputArg = None;
    emitArg = None;
    typeCheckArg = True;
    skipNext = False;
    versionNum = 1;
    
    
    for s in range(0,len(sys.argv)):
        if (skipNext):
            skipNext = False;
            continue;

        if (sys.argv[s] == '-f'):
            if (s + 1< len(sys.argv)):
                inputFilenameArg = sys.argv[s+1];
                skipNext = True;
            else:
                #will force printing usage without doing any work.
                helpArg = True;

        if (sys.argv[s] == '-v'):
            if (s + 1 < len(sys.argv)):
                versionNum = int(sys.argv[s+1]);
                skipNext = True;
                if (versionNum != 1) and (versionNum != 2):
                    print('\nI can only handle Waldo versions 1 or 2.\n');
                    helpArg = True;

                
        if (sys.argv[s] == '-go'):
            if (s+1 < len(sys.argv)):
                graphicalOutputArg = parseGraphicalOutputArg(sys.argv[s+1]);
                skipNext = True;
            else:
                #will force printing usage without doing any work.
                helpArg = True;

        if (sys.argv[s] == '-tc'):
            if (s+1 < len(sys.argv)):
                
                typeCheckArg = sys.argv[s+1];
                skipNext = True;
                if((typeCheckArg == 'true') or (typeCheckArg == 'True')):
                    typeCheckArg = True;
                elif((typeCheckArg == 'false') or (typeCheckArg == 'False')):
                    typeCheckArg = False;
                else:
                    helpArg = True;
                    print('\nCannot parse type check option.\n');
                    break;

                
        if (sys.argv[s] == '-to'):
            if (s+1 < len(sys.argv)):
                textOutputArg = sys.argv[s+1];
                skipNext = True;
            else:
                #will force printing usage without doing any work.
                helpArg = True;

        if (sys.argv[s] == '-h'):
            helpArg = True;

        if (sys.argv[s] == '-p'):
            printOutputArg = True;

        if (sys.argv[s] == '-e'):
            if (s+1 < len(sys.argv)):
                emitArg = sys.argv[s+1]
                skipNext = True;
            else:
                helpArg = True;

            

    if (helpArg):
        printUsage();
    else:
        if (inputFilenameArg == None):
            runTests();
        else:
            handleArgs(inputFilenameArg,graphicalOutputArg,textOutputArg,printOutputArg,typeCheckArg,emitArg,versionNum);
            