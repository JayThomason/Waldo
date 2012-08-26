#!/usr/bin/env python

import sys;
import os;
import emitUtils;

curDir = os.path.dirname(__file__);

# so can get ast labels
sys.path.append(os.path.join(curDir,'..','..','parser','ast'));
from astLabels import *;


def emitEndpoints(astRootNode,fdepDict):
    '''
    @returns {String}
    '''
    returner = '';

    # get endpoint names to process
    endpointNames = _getEndpointNames(astRootNode);

    
    returner += _emitEndpoint(endpointNames[0],astRootNode,fdepDict,0);
    returner += _emitEndpoint(endpointNames[1],astRootNode,fdepDict,1);

    return returner;


def _emitEndpoint(endpointName,astRootNode,fdepDict,whichEndpoint):
    '''
    Emits the endpoint class associated with the endpoint named
    endpointName
    
    @param {String} endpointName
    @param {AstNode} astRootNode
    @param {dict} fdepDict
    
    @param {0 or 1} whichEndpoint --- There are a couple of
    assymetries in endpoint construction.  For example, one enpdoint
    assigns event ids that are even and one assigns event ids that are
    odd.  This bit allows me to distinguish which endpoint I am emitting.
    '''

    sharedVariableNames = _getSharedIdentifiers(astRootNode);
    endpointVariableNames = _getEndpointVariableIdentifiersFromEndpointName(endpointName,astRootNode);
    # endpointFunctionNames = _getEndpointFunctionNames(endpointName,astRootNode);


    returner = 'class ' + endpointName + '(_Endpoint):\n';

    initMethod = 'def __init__(self,connectionObj):\n\n';
    initMethodBody = '';
    
    # create glob shared read vars dict: keeps track of number of
    # running events that are using one of the endpoint global or
    # shared variables for a read operation.
    globSharedVarsDict = {};
    for sharedVarName in sharedVariableNames:
        # each starts at 0 because there is no outstanding event that
        # is using the variable.
        globSharedVarsDict [ "'" + sharedVarName + "'"] = '0';
    for endpointVarName in endpointVariableNames:
        globSharedVarsDict [ "'" + endpointVarName + "'"] = '0';

    initMethodBody += emitUtils.createDictLiteralAssignment(
        'globSharedReadVars',globSharedVarsDict);
    initMethodBody += '\n';

    # create glob shared write vars dict.  @see comment above for glob
    # shared read vars dict, except of writes.
    initMethodBody += emitUtils.createDictLiteralAssignment(
        'globSharedWriteVars',globSharedVarsDict);
    initMethodBody += '\n\n';    


    # one endpoint can only assign even event ids the other can only
    # assign odd endpoint ids.
    evenOddEventId = whichEndpoint;
    otherEvenOdd = (evenOddEventId +1) % 2;
    initMethodBody += '# the other endpoint will have ' + str(otherEvenOdd) + '\n';
    initMethodBody += 'lastIdAssigned = ' + str(evenOddEventId) + ';\n\n';
    initMethodBody += '''# one side must be greater than the other
# used to resolve which side will back out its changes when
# there is a conflict.  (Currently though, these are unused.)
'''
    initMethodBody += 'myPriority = ' + str(evenOddEventId) + ';\n';
    initMethodBody += 'otherPriority = ' + str(otherEvenOdd) + ';\n\n';

    # handle context
    initMethodBody += 'committedContext = _Context();\n';


    # create a prototype events dict for this endpoint to copy active
    # events from.
    initMethodBody += '''
# make copy from base prototype events dict, setting myself as
# endpoint for each copied event.
prototypeEventsDict = {};
for pEvtKey in _PROTOTYPE_EVENTS_DICT.keys():
    pEvt = _PROTOTYPE_EVENTS_DICT[pEvtKey];
    prototypeEventsDict[pEvtKey] = pEvt.copy(self);
''';


    errMsg = '\nBehram error: still need to emit map of functions to ';
    errMsg += 'internal function names,endpoint init, and on create.\n';
    print(errMsg);
    
    initMethod += emitUtils.indentString(initMethodBody,1);
    returner += emitUtils.indentString(initMethod,1);
    return returner;


def _getSharedIdentifiers(astRoot):
    '''
    @returns {Array} --- returns an array of identifiers (annotated by
    slicer code) for shared variables.
    '''
    returner = [];
    
    sharedSectionNode = astRoot.children[3];
    for annotatedDeclarationNode in sharedSectionNode.children:
        # have an annotatedDeclarationNode for each shared variable.
        identifierNode = annotatedDeclarationNode.children[2];
        identifierNode._debugErrorIfHaveNoAnnotation('_getSharedIdentifiers');
        returner.append(identifierNode.sliceAnnotationName);

    return returner;


def _getEndpointVariableIdentifiersFromEndpointName(endpointName,astRootNode):
    endpoint1Node = astRootNode.children[4];
    endpoint1Name = endpoint1Node.children[0].value;
    
    endpoint2Node = astRootNode.children[5];
    endpoint2Name = endpoint2Node.children[0].value;
    
    
    toCheckEndpointNode = None;
    if endpointName == endpoint1Name:
        toCheckEndpointNode = endpoint1Node;
    elif endpointName == endpoint2Name:
        toCheckEndpointNode = endpoint2Node;
    else:
        errMsg = '\nBehram error: have no endpoint that ';
        errMsg += 'matches name "' + endpointName + '" to ';
        errMsg += 'gather shared variables from.\n';
        print(errMsg);
        assert(False);
        
    return _getEndpointVariableIdentifiersFromEndpointNode(toCheckEndpointNode);
    
def _getEndpointVariableIdentifiersFromEndpointNode(endpointNode):
    '''
    @param {AstNode} endpointNode --- AstNode with label AST_ENDPOINT

    @returns {array} --- Returns an array of annotated identifiers for
    each of the endpoint's variables.
    '''

    returner = [];
    if endpointNode.label != AST_ENDPOINT:
        errMsg = '\nBehram error: Error _getEndpointVariableIdentifiersFromEndpointNode ';
        errMsg += 'expected an ast node labeled as an endpoint.\n';
        print(errMsg);
        assert(False);

    endpointBodyNode = endpointNode.children[1];
    endpointGlobalsSectionNode = endpointBodyNode.children[0];

    for declNode in endpointGlobalsSectionNode.children:
        identifierNode = declNode.children[1];
        identifierNode._debugErrorIfHaveNoAnnotation('_getEndpointVariableIdentifiersFromEndpointNode');
        returner.append(identifierNode.sliceAnnotationName);

    return returner;
    

def _getEndpointNames(astRoot):
    returner = [];
    aliasSection = astRoot.children[1];
    returner.append(aliasSection.children[0].value);
    returner.append(aliasSection.children[1].value);
    return returner;
    
    
