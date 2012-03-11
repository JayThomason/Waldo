#!/usr/bin/python

import sys;
sys.path.append('d3');
import treeDraw;
from astLabels import *;
from astTypeCheckStack import TypeCheckContextStack;

def indentText(text,numIndents):
    returner = '';
    for s in range(0,numIndents):
        returner += '\t'
    returner += text;
    return returner;

def isEmptyAstNode(node):
    return (node.type == "EMPTY");

        
class AstNode():
    
    def __init__(self,_label,_lineNo=None,_linePos=None,_value=None):
        '''
        Only leaf nodes have values that are not None.
        (Things like Numbers, Strings, Identifiers, etc.)
        '''
        self.label    = _label;
        self.value    = _value;
        self.lineNo   = _lineNo;
        self.linePos  = _linePos;
        self.type     = None;
        self.note     = None;
        self.children = [];

    def setNote(self,note):
        self.note = note;
        
    def addChild(self, childToAdd):
        self.children.append(childToAdd);

        
    def addChildren(self, childrenToAdd):
        for s in childrenToAdd:
            self.children.append(s);
        
    def getChildren(self):
        return self.children;

    def printAst(self,filename=None):
        text = self.toJSON();
        if (filename != None):
            filer = open(filename,'w');
            filer.write(text);
            filer.flush();
            filer.close();
        else:
            print(self.toJSON());


    def typeCheck(self,progText,typeStack=None):
        #based on types of children, check my type.  Also, pass up
        #line numbers.
        
        if ((self.label != AST_ROOT) and (typeStack == None)):
            print('\nError.  Must have typeStack unless root node\n');
            assert(False);
        elif(self.label == AST_ROOT):
            typeStack = TypeCheckContextStack();

        if ((self.label == AST_ROOT) or
            (self.label == AST_FUNCTION_BODY) or
            (self.label == AST_SHARED_SECTION) or
            (self.label == AST_ENDPOINT_FUNCTION_SECTION)):
            #each of these create new contexts.  don't forget to
            #remove several of them at the bottom of the function.
            typeStack.pushContext();


        if(self.label == AST_ROOT):
            #top of program

            #getting protocol object name
            typeStack.protObjName = self.children[0].value;

            #handling alias section
            aliasSection = self.children[1];

            #endpoint 1
            typeStack.endpoint1 = aliasSection.children[0].value; 
            typeStack.endpoint1LineNo = aliasSection.children[0].lineNo;

            #endpoint 2
            typeStack.endpoint2 = aliasSection.children[1].value; 
            typeStack.endpoint2LineNo = aliasSection.children[1].lineNo;
            
            if (typeStack.endpoint1 == typeStack.endpoint2):
                errorFunction('Cannot use same names for endpoints',[typeStack.endpoint1,typeStack.endpoint2],[typeStack.endpoint1LineNo,typeStack.endpoint2LineNo],progText);

            #get into shared section
            #note: shared section should leave its context on the stack.
            self.children[3].typeCheck(progText,typeStack);

            #check one endpoint
            self.children[4].typeCheck(progText,typeStack);

            print('\nWarning, still need to add other endpoint to parser for checking\n');
            
            #go back and type check trace items.  see notes in
            #corresponding elif.
            self.children[2].typeCheck(progText,typeStack);
                

        elif(self.label == AST_TRACE_SECTION):
            '''
            need to check that first part of all TraceItems correspond to an Endpoint.
            need to check that alternate between Endpoints
            need to check that no two traces begin with same TraceItem
            need to check to ensure all functions referenced match with msg_send and msg_receive (probably can't do that part at this point.  Maybe later).
            '''
            print('\nTo do: still must type check trace section\n');

        elif(self.label == AST_SHARED_SECTION):
            #each child will be an annotated declaration.
            for s in self.children:
                s.typeCheck(progText,typeStack);

        elif(self.label == AST_ANNOTATED_DECLARATION):
            # the type of this identifier
            #reset my type to it.
            self.type = self.children[1].value;
            currentLineNo = self.children[1].lineNo;
            if (len(self.children) == 4):
                #have an initializer too.
                self.children[3].typeCheck(progText,typeStack);
                assignType = self.children[3].type;
                if (assignType != self.type):
                    if (assignType == None):
                        assignType = '<None>';
                    errorString = 'Assigned type [' + assignType + '] does not ';
                    errorString += 'match declared type [' + self.type + '].';
                    errorFunction(errorString,[self],[currentLineNo],progText);

            #actually store the new type
            identifierName = self.children[2].value;
            existsAlready = typeStack.getIdentifierType(identifierName);
            if (existsAlready != None):
                errorFunction('Already have an identifier named ' + identifierName,[self],[currentLineNo, existsAlready.lineNo],progText);
            else:
                typeStack.addIdentifier(identifierName,self.type,currentLineNo);
            
        elif(self.label == AST_NUMBER):
            self.type = TYPE_NUMBER;
        elif(self.label == AST_STRING):
            self.type = TYPE_STRING;
        elif(self.label == AST_BOOL):
            self.type = TYPE_BOOL;
        elif(self.label == AST_FUNCTION_CALL):
            print('\nNeed to finish type checking for AST_FUNCTION_CALL\n');

            
        elif(self.label == AST_ENDPOINT):
            print('\nStill need to add type checking to endpoint section\n');


        #remove the new context that we had created.  Note: shared
        #section is intentionally missing.  Want to maintain that 
        #context while type-checking the endpoint sections.
        if ((self.label == AST_ROOT) or
            (self.label == AST_FUNCTION_BODY) or
            (self.label == AST_ENDPOINT_FUNCTION_SECTION)):
            
            typeStack.popContext();







            
    def toJSON(self,indentLevel=0,drawHigh=False):
        '''
        JSON format:
        {
            "name": "<self.label>",
            "type": "<self.type>",
            "value": <self.value>,
            "drawHigh": drawHigh
            "children": [
                   //recurse
              ]
        }
        '''
        #name print
        returner = indentText('{\n',indentLevel);
        returner += indentText('"name": "',indentLevel+1);
        returner += self.label;
        returner += '"';


        if (self.value != None):
            returner += ',\n';
            returner += indentText('"value": "',indentLevel+1);
            returner += self.value;
            returner += '"'

        
        if (self.type != None):
            returner += ',\n';
            returner += indentText('"type": "',indentLevel+1);
            returner += self.type;
            returner += '"'


        #print drawHigh
        returner += ',\n';
        returner += indentText('"drawHigh": ',indentLevel+1);
        if (drawHigh):
            returner += 'true';
        else:
            returner += 'false';
            
            
        #child print
        if (len(self.children) != 0):
            returner += ',\n';
            returner += indentText('"children": [\n',indentLevel+1);

            for s in range(0,len(self.children)):
                drawHigh = not drawHigh;
                returner += self.children[s].toJSON(indentLevel+1,drawHigh);
                if (s != (len(self.children) -1 )):
                    returner += ',\n';
            returner += ']';

        #close object
        returner += '\n' + indentText('}',indentLevel);
        return returner;

    
    def drawPretty(self,filename,pathToD3='d3',width=5000,height=3000):
        '''
        For now, an ugly way of generating a pretty view 
        '''

        #default args did not work how I anticipated.
        if (pathToD3 == None):
            pathToD3 = 'd3';
        if(width == None):
            width = 5000;
        if(height==None):
            height = 3000;
            
        treeDraw.prettyDrawTree(filename=filename,data=self.toJSON(),pathToD3=pathToD3,width=width,height=height);


ERROR_NUM_LINES_EITHER_SIDE = 4;
        
def errorFunction(errorString,astNodes,lineNumbers,progText):
    '''
    @param {String} errorString -- Text associated with error.
    @param {Array < AstNode>} astNodes -- Contains all ast nodes associated with the error.
    @param {Array < Int> } lineNumbers -- Contains all line numbers associated with error.
    @param {String} progText -- The source text of the program.
    '''
    
    print('\n\n');
    print('*************************');
    print('Error in type checking:');
    print(errorString);

    print('-------\nAST node labels:');
    for s in astNodes:
        print(s.label)
        
    print('-------\nLine numbers:');
    for s in lineNumbers:
        print(s);

    programTextArray = progText.split('\n');
    print('-------\nProgram text:');
    for errorLine in lineNumbers:
        print('\n\n');
        lowerLineNum = max(0,errorLine - ERROR_NUM_LINES_EITHER_SIDE);
        upperLineNum = min(len(programTextArray),errorLine + ERROR_NUM_LINES_EITHER_SIDE);

        for s in range(lowerLineNum, upperLineNum):
            errorText = '';
            errorText += str(s+1);

            if (s == errorLine -1):
                errorText += '*   ';
            else:
                errorText += '    ';
                    
            errorText += programTextArray[s];
            print(errorText);

        
    print('*************************');
    print('\n\n');

