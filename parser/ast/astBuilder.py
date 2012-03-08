#!/usr/bin/python

import sys;
sys.path.append('../../lexer/')
from waldoLex import tokens;
from waldoLex import constructLexer;

from astNode import AstNode;
import ply.yacc as yacc;




# Overall Structure:
# NameSection
# EndpointAliasSection
# TraceSection
# SharedSection
# EndpointSection
# EndpointSection ... not necessary if have symmetric names....


#AST_TOKENS
AST_ROOT = 'ROOT';
AST_PROT_OBJ_NAME = 'PROT_OBJ_NAME';
AST_ENDPOINT_ALIAS_SECTION = 'ALIAS_SECTION';
#traces
AST_TRACE_SECTION = 'TRACE_SECTION';
AST_TRACE_BODY_SECTION = 'TRACE_BODY_SECTION';   #INTERMEDIATE
AST_TRACE_ITEM = 'TRACE_ITEM';
AST_TRACE_LINE = 'TRACE_LINE';

#shared
AST_SHARED_SECTION = 'SHARED_SECTION';
AST_SHARED_BODY_SECTION = 'SHARED_BODY_SECTION';
AST_ANNOTATED_DECLARATION = 'ANNOTATED_DECLARATION';
    

AST_IDENTIFIER = 'IDENTIFIER';
AST_EMPTY = 'EMPTY';

#note: otherwise, starts at first rule.  
start = 'RootExpression';
#need to have something named lexer for parser to chew into
lexer = constructLexer();


def p_RootExpression(p):
    'RootExpression : NameSection EndpointAliasSection TraceSection SharedSection';
    p[0] = AstNode(AST_ROOT,p.lineno(0),p.lexpos(0));
    p[0].addChildren([p[1],p[2],p[3],p[4]]);
    

def p_NameSection(p):
    'NameSection : Identifier'
    p[0] = AstNode(AST_PROT_OBJ_NAME,p.lineno(0),p.lexpos(0));
    p[0].addChild(p[1]);

def p_EndpointAliasSection(p):
    'EndpointAliasSection : ENDPOINT Identifier SEMI_COLON ENDPOINT Identifier SEMI_COLON';
    p[0] = AstNode(AST_ENDPOINT_ALIAS_SECTION,p.lineno(0),p.lexpos(0));
    p[0].addChildren([p[2], p[5]]);

def p_TraceSection(p):
    'TraceSection : TRACES CURLY_LEFT TraceBodySection CURLY_RIGHT';
    #note: this is an intermediate production, and will get skipped.
    p[0] = AstNode(AST_TRACE_SECTION,p.lineno(0),p.lexpos(0));
    
    #getting TraceBodySection's children removes it as an intermediate node.
    p[0].addChildren(p[3].getChildren());


def p_TraceItem(p):
    'TraceItem : Identifier DOT Identifier'
    #Each TraceItem is connected by arrows in Trace section
    # TraceItem -> TraceItem -> TraceItem;
    p[0] = AstNode(AST_TRACE_ITEM,p.lineno(1),p.lexpos(1));
    p[0].addChildren([p[1],p[3]]);

def p_TraceBodySection(p):
    '''TraceBodySection : TraceLine SEMI_COLON TraceBodySection
                        | TraceLine SEMI_COLON''';
    #note: currently, cannot have empty trace body section.
    p[0] = AstNode(AST_TRACE_BODY_SECTION,p.lineno(0),p.lexpos(0));
    p[0].addChild(p[1]);
    if(len(p) == 4):
        #flattens all TraceLines into siblings
        p[0].addChildren(p[3].getChildren());
    

def p_TraceLine(p):
    '''TraceLine : TraceItem  SEND_ARROW TraceLine
                 | TraceItem  '''

    p[0] = AstNode(AST_TRACE_LINE,p.lineno(0),p.lexpos(0));
    p[0].addChild(p[1]);
    if (len(p) == 4):
        #have additional parts of trace body to grab.
        p[0].addChildren(p[3].getChildren());

def p_SharedSection(p):
    '''SharedSection : SHARED CURLY_LEFT SharedBodySection CURLY_RIGHT
                     | SHARED CURLY_LEFT empty CURLY_RIGHT''';

    p[0] = AstNode(AST_SHARED_SECTION,p.lineno(0),p.lexpos(0));
    p[0].addChild(p[3]);

def p_SharedBodySection(p):
    '''SharedBodySection : AnnotatedDeclaration SEMI_COLON SharedBodySection
                         | AnnotatedDeclaration SEMI_COLON'''
    #note: currently, cannot have empty shared section.
    p[0] = AstNode(AST_SHARED_BODY_SECTION, p.lineno(0),p.lexpos(0));
    p[0].addChild(p[1]);
    if (len(p) == 4):
        p[0].addChildren(p[3].getChildren());
    
def p_AnnotatedDeclaration(p):
    'AnnotatedDeclaration : Identifier'
    p[0] = AstNode(AST_ANNOTATED_DECLARATION,p.lineno(1),p.lexpos(1));


    
def p_empty(p):
    'empty : ';
    p[0] = AstNode(AST_EMPTY, p.lineno(0),p.lexpos(0));
    
    
def p_Identifier(p):
    'Identifier : IDENTIFIER';
    p[0] = AstNode(AST_IDENTIFIER,p.lineno(1),p.lexpos(1),p[1]);
    
def p_error(p):
    print "Syntax error at '%s'" % p.value

def getParser():
    returner = yacc.yacc();
    return returner;

