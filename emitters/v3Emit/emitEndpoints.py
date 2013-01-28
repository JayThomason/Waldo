#!/usr/bin/env python

import sys;
import os;
import emitUtils;
import mainEmit;

# so can get ast labels
from parser.ast.astLabels import *
import parser.ast.typeCheck as TypeCheck
from parser.ast.astBuilderCommon import isEmptyNode


# so can get oncreate token name
from lexer.waldoLex import ONCREATE_TOKEN

from emitUtils import _convertSrcFuncNameToInternal;



def emitEndpoints(astRootNode,fdepDict,emitContext):
    '''
    @returns {String}
    '''
    returner = '';

    # get endpoint names to process
    endpointNames = emitUtils.getEndpointNames(astRootNode);


    # may require some additional setup depending on emit context
    if emitContext.collisionFlag:
        returner += '\n#### DEBUG';
        returner += '\n# before the send of every message sequence, time.sleep this ';
        returner += '\n# long to try to introduce collisions in transactions.';
        returner += '\n_COLLISION_TIMEOUT_VAL = .4;';
        returner += '\n#### END DEBUG\n\n';
    
    returner += _emitEndpoint(
        endpointNames[0],astRootNode,fdepDict,0,emitContext);
    
    returner += _emitEndpoint(
        endpointNames[1],astRootNode,fdepDict,1,emitContext);

    
    return returner;


def _emitEndpoint(
    endpointName,astRootNode,fdepDict,whichEndpoint,emitContext):
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

    @param {EmitContext object} emitContext --- @see class EmitContext
    in emitUtils.py
    '''
    returner = 'class ' + endpointName + '(_Endpoint):\n';
    # handle init
    returner += emitUtils.indentString(
        _emitInit(endpointName,astRootNode,fdepDict,whichEndpoint,emitContext),
        1);
    returner += '\n\n';

    # handle each user-defined oncreate, public, and private function.
    returner += emitUtils.indentString('###### USER DEFINED FUNCTIONS #######\n\n',1);
    functionSectionNode = _getFunctionSectionNode(
        endpointName,astRootNode);
    for funcNode in functionSectionNode.children:
        returner += emitUtils.indentString(
            _emitPublicPrivateOnCreateFunctionDefinition(
                funcNode,endpointName,astRootNode,fdepDict,emitContext),
            1);
        returner += '\n\n';

    # handle message sequence functions
    returner += emitUtils.indentString('###### User-defined message sequence functions #######\n',1);
    returner += emitUtils.indentString(
        '''
# FIXME: For now, making message send functions private.  This
# means that an internal function must call the message send and
# that _callTypes are restricted to only being from internal.

# message receive functions are treated as internal and cannot
# have a first_from_external call type and both its _actEvent
# and _context must be defined.

''',1);
    
    allMessageFunctionNodes = _getMessageFunctionNodes(endpointName,astRootNode);
    for msgFuncNodeSharedObj in allMessageFunctionNodes:

        if not msgFuncNodeSharedObj.isOnComplete():
            # non oncomplete nodes should be indented because they are
            # a part of the class.
            returner += emitUtils.indentString(
                msgFuncNodeSharedObj.emitMessageFunctionDefinition(
                    endpointName,astRootNode,fdepDict,emitContext),
                1);
            returner += '\n\n';

    returner += ('\n##### Emitting all on complete functions for endpoint "%s"\n' %
                 endpointName);
    for msgFuncNodeSharedObj in allMessageFunctionNodes:
        if msgFuncNodeSharedObj.isOnComplete():
            # oncomplete nodes should not be indented because they are
            # not part of the class
            returner += msgFuncNodeSharedObj.emitMessageFunctionDefinition(
                endpointName,astRootNode,fdepDict,emitContext);

            returner += '\n\n';

    return returner;


def _publicFunctionBodyDefinition(
    externalFuncArguments,funcArguments,funcName,funcNode):
    '''
    @param{Array} externalFuncArguments --- Each element is the name
    of an argument to this function that is an external variable.

    @param{Array} funcArguments --- Each element is the name of a
    variable that was pased in.
    
    @param{String} funcName --- The name of the public function (it
    gets mangled to a private function that we call)

    @param{AstNode} funcNode --- The AstNode for this public function
    '''

    publicMethodBody = '\n# put the external object in the external store\n';
    extArgString = '';
    for extFuncArg in externalFuncArguments:
        publicMethodBody +='''
self._externalStore.incrementRefCountAddIfNoExist(
    self._endpointName,%s);
''' % extFuncArg;

        extArgString += extFuncArg + ',';

    publicMethodBody = '''# passing in FUNCTION_ARGUMENT_CONTROL_FIRST_FROM_EXTERNAL
# ... that way know that the function call happened from
# external caller and don't have to generate new function
# calls for it.
_returner = self.%s('''% _convertSrcFuncNameToInternal(funcName);
    
    # insert function arguments
    publicMethodBody += '_Endpoint._FUNCTION_ARGUMENT_CONTROL_FIRST_FROM_EXTERNAL,None,None';
    for argName in funcArguments:
        
        publicMethodBody += ','

        # if the argument is a list or a map, then we have to deep
        # copy it into a WaldoMap or WaldoList object.  
        if _argIsNonExternalMap(funcNode,argName):
            publicMethodBody += '_WaldoMap(' + argName + ',True)'
        elif _argIsNonExternalList(funcNode,argName):
            publicMethodBody += '_WaldoList(' + argName + ',True)'
        else:
            publicMethodBody += argName

    publicMethodBody += ');\n';

    publicMethodBody += '''
# should check if there are other active events
self._tryNextEvent();

# to release reference count I took on external argument
# passed in and to garbage collect any externals with no
# references.

_extInterfaceCleanup = _ExtInterfaceCleanup(
    [%s],self._externalStore,self._endpointName);
_extInterfaceCleanup.start();

_new_returner = []
''' % extArgString

    return_node = _get_func_return_node(funcNode)

    for return_node_counter in range(0,len(return_node.children)):
        return_type_node  = return_node.children[return_node_counter]
        
        if (TypeCheck.templateUtil.isMapType(return_type_node.type) or
            TypeCheck.templateUtil.isListType(return_type_node.type)):
            
            if return_type_node.external != None:
                # copy the return node
                publicMethodBody += '''
_new_returner.append(_returner[%s]._map_list_copy_return())
''' % str(return_node_counter)
                continue

        publicMethodBody += '''
_new_returner.append(_returner[%s])
''' % str(return_node_counter)

        
    
    publicMethodBody += '''
if len(_new_returner) == 1:
    return _returner[0]

return tuple(_new_returner)

'''
    publicMethodBody += '\n'


    returner = emitUtils.indentString(publicMethodBody,1);
    returner += '\n';
    return returner


def _get_func_return_node(func_node):
    '''
    Note: asserts out if func_node isn't private or public.
    '''
    return_node_index = _getReturnTypeIndexFromFuncNodeLabel(
        func_node.label)
    
    return_node = func_node.children[return_node_index]
    return return_node
    

def _argIsNonExternalMap(func_node,arg_name):
    '''
    @param{AstNode} func_node ---

    @param{String} arg_name --- The name of the argument the

    @returns{Bool} True if the argument named arg_name of the function
    contained in func_node is a map type and not an external variable.
    False otherwise.
    '''
    if func_node.label == AST_MESSAGE_RECEIVE_SEQUENCE_FUNCTION:
        err_msg = '\nBehram error: message_receive_sequence_functions '
        err_msg += 'do not have arguments.\n'
        print err_msg
        assert(False)

    argNodeIndex = _getArgumentIndexFromFuncNodeLabel(func_node.label);
    if argNodeIndex == None:
        errMsg = '\nBehram error: cannot call argumentnamesfromfuncnode on ';
        errMsg += 'nodes that are not function nodes.\n';
        print(errMsg);
        assert(False);

    returner = [];
    funcDeclArgListNode = func_node.children[argNodeIndex];
    for funcDeclArgNode in funcDeclArgListNode.children:
        name_node = funcDeclArgNode.children[1]
        type_node = funcDeclArgNode.children[0]
        name = name_node.value
        if type_node.external != None:
            return False
        elif name == arg_name:
            if TypeCheck.templateUtil.isMapType(type_node.type):
                return True
            else:
                return False
    err_msg = '\nBehram error.  Funtion does not have an argument named "'
    err_msg += arg_name + '."\n'
    print err_msg
    assert (False)


def _argIsNonExternalList(func_node,arg_name):
    '''
    @see _argIsMap, except for list types
    '''
    if func_node.label == AST_MESSAGE_RECEIVE_SEQUENCE_FUNCTION:
        err_msg = '\nBehram error: message_receive_sequence_functions '
        err_msg += 'do not have arguments.\n'
        print err_msg
        assert(False)

    argNodeIndex = _getArgumentIndexFromFuncNodeLabel(func_node.label);
    if argNodeIndex == None:
        errMsg = '\nBehram error: cannot call argumentnamesfromfuncnode on ';
        errMsg += 'nodes that are not function nodes.\n';
        print(errMsg);
        assert(False);

    returner = [];
    funcDeclArgListNode = func_node.children[argNodeIndex];
    for funcDeclArgNode in funcDeclArgListNode.children:
        name_node = funcDeclArgNode.children[1]
        type_node = funcDeclArgNode.children[0]
        name = name_node.value
        if name == arg_name:
            if type_node.external != None:
                return False
            elif TypeCheck.templateUtil.isListType(type_node.type):
                return True
            else:
                return False
    err_msg = '\nBehram error.  Funtion does not have an argument named "'
    err_msg += arg_name + '."\n'
    print err_msg
    assert (False)

    
def _emitPublicPrivateOnCreateFunctionDefinition(
    funcNode,endpointName,astRootNode,fdepDict,emitContext):
    '''
    @param {AstNode} funcNode --- Should be the root node of the
    function we're trying to emit.  only valid labels are oncreate,
    public, private, message send, message receive.
    
    @param {String} endpointName --- The name of the endpoint that
    we're emitting this function for.
    
    @param {AstNode} astRootNode --- The root ast node of the entire
    program.
    '''

    funcNameNode = funcNode.children[0];
    funcName = funcNameNode.value;
    funcArguments = _getArgumentNamesFromFuncNode(funcNode);

    functionBodyNode = _getFuncBodyNodeFromFuncNode(funcNode);    
    
    returner = '';


    if funcNode.label == AST_PUBLIC_FUNCTION:
        externalFuncArguments = _getExternalArgumentNamesFromFuncNode(funcNode);
        # here we emit the public version.
        returner += 'def ' + funcName + '(self,';
        for argName in funcArguments:
            returner += argName + ',';
        returner += '):\n';
        returner += _publicFunctionBodyDefinition(
            externalFuncArguments,funcArguments,funcName,funcNode)


    ####### now handle internal definition of function #########
    # every function should have a special key associated in the event
    # dict.  this is used so that we know where to re-start execution
    # after an event completes.  
    functionEventKey = emitUtils.getFuncEventKey(funcName,endpointName,fdepDict);
    
    # actually emit the function    
    returner += 'def %s(self,' % _convertSrcFuncNameToInternal(funcName);
    returner += '_callType,_actEvent,_context'    
    for argName in funcArguments:
        returner += ',' + argName;

    returner += '):\n';


    funcBody = r"""'''
@param{String} _callType ---

   _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED :
   means that anything that we return will not be set in
   return statement of context, but rather will just be
   returned.

   _Endpoint._FUNCTION_ARGUMENT_CONTROL_RESUME_POSTPONE :
   means that we should return anything that we get via the
   _context return queue, but that we should *not* create a
   new active event or context.

   _Endpoint._FUNCTION_ARGUMENT_CONTROL_FIRST_FROM_EXTERNAL :
   means that we should return anything that we get via the
   _context return queue, *and* we should create a new active
   event and context.


Note that the only time that _actEvent and _context should be
empty is on a FIRST_FROM_EXTERNAL call.

@param{_ActiveEvent object} _actEvent --- Pass into subsequent
functions that this function calls from its body.  Used only
directly for RESUME_POSTPONE.  It is used to signal to the
blocking execution loop that the internal execution of the
function has completed and can try to return its value, commit
its context, and unblock.

@param{_Context object} _context --- Each function can operate
on endpoint global, sequence global, and shared variables.
These are all stored in this _context object.

'''

# FIXME: need to actually generate logic for deep-copying
# arguments


#### DEBUG
if ((_callType != _Endpoint._FUNCTION_ARGUMENT_CONTROL_FIRST_FROM_EXTERNAL) and
    (_callType != _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED) and
    (_callType != _Endpoint._FUNCTION_ARGUMENT_CONTROL_RESUME_POSTPONE)):
    errMsg = '\nBehram error: invalid call type passed to function.\n';
    print(errMsg);
    assert(False);

if _callType == _Endpoint._FUNCTION_ARGUMENT_CONTROL_FIRST_FROM_EXTERNAL:
    if _actEvent != None:
        errMsg = '\nBehram error: when issuing call from external, should ';
        errMsg += 'have an empty _actEvent argument.\n';
        print(errMsg);
        assert(False);

    if _context != None:
        errMsg = '\nBehram error: when issuing call from external, should ';
        errMsg += 'have an empty _context argument.\n';
        print(errMsg);
        assert(False);

if ((_callType ==  _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED) or
    (_callType == _Endpoint._FUNCTION_ARGUMENT_CONTROL_RESUME_POSTPONE)):
    if _actEvent == None:
        errMsg = '\nBehram error: when issuing non-external call, should ';
        errMsg += '*not* have an empty _actEvent argument.\n';
        print(errMsg);
        assert(False);
    if _context == None:
        errMsg = '\nBehram error: when issuing non-external call, should ';
        errMsg += '*not* have an empty _context argument.\n';
        print(errMsg);
        assert(False);
#### END DEBUG


# need to create the event and either create its context and
# execute it if the required read/write variables are
# available, or schedule the event for the future if those
# resources are not available.
if _callType == _Endpoint._FUNCTION_ARGUMENT_CONTROL_FIRST_FROM_EXTERNAL:
    # to get argument values
    # see http://stackoverflow.com/questions/582056/getting-list-of-parameters-inside-python-function
    _frame = _inspect.currentframe();
    _args, _, _, _values = _inspect.getargvalues(_frame);
    _functionArgs = [_values[i] for i in _args];

    # remove head argument (self) and tail default arguments
    # (_callType, _actEvent, and _context) off the
    # back, because these will be automatically filled when
    # function is called internally.
    _functionArgs = _functionArgs[4:];

    self._lock(); # locking at this point, because call to
                  # generateActiveEvent, uses the committed dict.

    _actEvent = self._prototypeEventsDict['""" + functionEventKey + r"""'].generateActiveEvent(None)
    _actEvent.setToExecuteFrom('""" + functionEventKey + r"""'); # when postponed, will return to here
    _actEvent.setArgsArray(_functionArgs);

    _eventAdded,_context,_res_req_results = _actEvent.addEventToEndpointIfCan();

    if not _eventAdded:
        # conflict with globals/shareds .... insert event into
        # toProcess array and block until function gets
        # executed.
        self._inactiveEvents.append(_actEvent);

    self._unlock();                                            

    if _eventAdded:

        self._executeActive(
            _actEvent,
            _context,
            # specified so that will use return queue when done, etc.
            _Endpoint._FUNCTION_ARGUMENT_CONTROL_RESUME_POSTPONE);                    

    # now block until we know that the event has been
    # completed....can block by waiting on thread safe return
    # queue.
    try:
        _returnQueueElement = _actEvent.returnQueue.get(
            True,""" + str(emitUtils.TIMEOUT_PARAMETER) + r""")
    except Queue.Empty:
        raise self._waldo_timeout_excep('Timed out') 
    return _returnQueueElement.returnVal;


####### ONLY GETS HERE IF CALL TYPE IS NOT FIRST_FROM_EXTERNAL
#### DEBUG
if _callType == _Endpoint._FUNCTION_ARGUMENT_CONTROL_FIRST_FROM_EXTERNAL:
    errMsg = '\nBehram error: should not execute body of function ';
    errMsg += 'if first from external.\n';
    print(errMsg);
    assert(False);
#### END DEUBG.

# actual meat of the function
""";

    # start emitting actual body of the function.
    for statementNode in functionBodyNode.children:
        funcBody += mainEmit.emit(endpointName,statementNode,fdepDict,emitContext);
        funcBody += '\n';

    # force a return at end of function if did not encounter one
    # otherwise (eg. statement did not return anything).  This ensures
    # that code that had been blocking on completion of this function
    # gets called
    funcBody += """
# special-cased return statement
if _callType == _Endpoint._FUNCTION_ARGUMENT_CONTROL_RESUME_POSTPONE:
    # note that also commit outstanding changes to context here.
    _actEvent.setCompleted([None],_context);
    return;
elif _callType == _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED:
    return [None];

""";
        
    returner += emitUtils.indentString(funcBody,1);

    #if we're emitting a public function, we must emit its twin run
    #and hold function
    returner += _emit_run_and_hold(
        funcNode,endpointName,astRootNode,fdepDict,emitContext)
    
    return returner;
    

def _emit_run_and_hold(
    func_node,endpoint_name,ast_root_node,fdep_ict,emit_context):
    '''
    @param {AstNode} funcNode --- Should be the root node of the
    function we're trying to emit.  only valid labels are oncreate,
    public, private, message send, message receive.
    
    @param {String} endpointName --- The name of the endpoint that
    we're emitting this function for.
    
    @param {AstNode} astRootNode --- The root ast node of the entire
    program.
    '''

    to_return = ''
    if func_node.label != AST_PUBLIC_FUNCTION:
        # only need to emit run and holds for public functions
        return to_return

    func_name_node = func_node.children[0]
    func_name = func_name_node.value
    func_arguments = _getArgumentNamesFromFuncNode(func_node);
    

    # handle function signature
    emitted_func_name = emitUtils.construct_hold_func_name(
        func_name,endpoint_name)
    func_head = 'def %s(self,_active_event,_context,*args):\n' % emitted_func_name

    # handle function body, which just calls internal method of public
    # function.
    func_body = 'return self.'
    func_body += _convertSrcFuncNameToInternal(func_name)
    func_body += '''(
    _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED,
    _active_event,
    _context,
    *args )

'''

    # indent + return
    to_return += func_head + emitUtils.indentString(func_body,1);
    return to_return

    

def _emitInit(endpointName,astRootNode,fdepDict,whichEndpoint,emitContext):
    '''
    For params, @see _emitEndpoint

    @returns {String} --- a non-indented raw text of init function for
    a single endpoint.
    '''
    sharedIdentifiersToDeclNodesDict = _getSharedIdsToDeclNodesDict(
        astRootNode);
    globalIdentifiersToDeclNodesDict = _getEndpointIdsToDeclNodesDict(
        endpointName,astRootNode);
    
    sharedVariableNames = sorted(
        sharedIdentifiersToDeclNodesDict.keys());
    
    endpointVariableNames = sorted(
        globalIdentifiersToDeclNodesDict.keys());


    onCreateNode = _getOnCreateNode(endpointName,astRootNode);
    onCreateArgumentNames = [];
    if onCreateNode != None:
        onCreateArgumentNames = _getArgumentNamesFromFuncNode(onCreateNode);
        externalOnCreateArgumentNames = _getExternalArgumentNamesFromFuncNode(onCreateNode);



    initMethod = 'def __init__(self,_waldo_timeout_excep,_connectionObj,_reservationManager,_waldo_id,_endpoint_id,';
    for argName in onCreateArgumentNames:
        initMethod += argName + ',';
    initMethod += '):\n\n'
    
    initMethodBody = '';

    # create glob shared read vars dict: keeps track of number of
    # running events that are using one of the endpoint global or
    # shared variables for a read operation.
    globSharedVarsDict = {};
    for sharedVarName in sharedVariableNames:
        # each starts at 0 because there is no outstanding event that
        # is using the variable.
        globSharedVarsDict [ "'" + sharedVarName + "'"] = '[]';
    for endpointVarName in endpointVariableNames:
        globSharedVarsDict [ "'" + endpointVarName + "'"] = '[]';

    initMethodBody += '''
# keeps track of the number of outstanding events that
# are using each variable for a read or a write.
'''
    initMethodBody += emitUtils.createDictLiteralAssignment(
        '_globSharedReadVars',globSharedVarsDict);
    initMethodBody += '\n';

    # create glob shared write vars dict.  @see comment above for glob
    # shared read vars dict, except of writes.
    initMethodBody += emitUtils.createDictLiteralAssignment(
        '_globSharedWriteVars',globSharedVarsDict);
    initMethodBody += '\n\n';    


    # each endpoint needs an external store.
    initMethodBody += '\nself._externalStore = _ExternalStore();\n';


    # one endpoint can only assign even event ids the other can only
    # assign odd endpoint ids.
    evenOddEventId = whichEndpoint;
    otherEvenOdd = (evenOddEventId +1) % 2;
    initMethodBody += '# the other endpoint will have ' + str(otherEvenOdd) + '\n';
    initMethodBody += '_lastIdAssigned = ' + str(evenOddEventId) + ';\n\n';
    initMethodBody += '''# one side must be greater than the other
# used to resolve which side will back out its changes when
# there is a conflict.  (Currently though, these are unused.)
'''
    initMethodBody += '_myPriority = ' + str(evenOddEventId) + '\n'
    initMethodBody += '_theirPriority = ' + str(otherEvenOdd) + '\n'
    
    # handle context
    initMethodBody += '_context = _Context(self._externalStore,\'%s\',self);\n' % endpointName;

    # create a prototype events dict for this endpoint to copy active
    # events from.
    initMethodBody += '''
# make copy from base prototype events dict, setting myself as
# endpoint for each copied event.
_prototypeEventsDict = {};
for _pEvtKey in _PROTOTYPE_EVENTS_DICT.keys():
    _pEvt = _PROTOTYPE_EVENTS_DICT[_pEvtKey];
    _prototypeEventsDict[_pEvtKey] = _pEvt.copy(self);
''';



    # create execFromInternalFuncDict, which maps event names to the
    # internal functions to call for them.

    initMethodBody += '''
# every event needs to be able to map its name to the internal
# function that should be called to initiate it.
# string(<id>__<iniating function name>) : string ... string
# is name of function on endpoint to call.
''';
    endpointFunctionNamesEventDict = _getEndpointFunctionNamesFromEndpointName(
        endpointName,astRootNode,fdepDict);

    # add refresh functions to the execFromToInternalFuncDict
    endpointFunctionNamesEventDict[
        "'"+emitUtils._REFRESH_KEY+"'"] = (
        "'" + emitUtils._REFRESH_SEND_FUNCTION_NAME + "'");
        
    endpointFunctionNamesEventDict[
        "'" + emitUtils._REFRESH_RECEIVE_KEY + "'"] = (
        "'" + emitUtils._REFRESH_RECEIVE_FUNCTION_NAME + "'");

    
    initMethodBody += emitUtils.createDictLiteralAssignment(
        '_execFromToInternalFuncDict',endpointFunctionNamesEventDict);

    initMethodBody += '\n\n';

    # now emit the externals dict
    externalsNamesDict = _getEndpointExternalsFromEndpointName(
        endpointName,astRootNode);

    initMethodBody += emitUtils.createDictLiteralAssignment(
        '_externalGlobals',externalsNamesDict);
    
    # now emit the base _Endpoint class initializer
    initMethodBody += '''

# invoke base class initializer
_Endpoint.__init__(
    self,_connectionObj,_globSharedReadVars,_globSharedWriteVars,
    _lastIdAssigned,_myPriority,_theirPriority,_context,
    _execFromToInternalFuncDict,_prototypeEventsDict, '%s',
    _externalGlobals, _reservationManager,_waldo_id,_endpoint_id,
    _waldo_timeout_excep);
''' % endpointName;
    
    initMethodBody += '\n\n';

    # now emit global and shared variable dictionaries.  each contains
    # their default values.  After this, actually initialize their
    # values according to user-coded initialization statements.

    # shareds
    sharedDict = {};
    for sharedId in sorted(sharedIdentifiersToDeclNodesDict.keys()):
        declNode = sharedIdentifiersToDeclNodesDict[sharedId];
        defaultVal = emitUtils.getDefaultValueFromDeclNode(declNode);
        sharedDict[ "'" + sharedId + "'"] = defaultVal;
        
    initMethodBody += '# emitting local copies of shared variables\n';
    initMethodBody += '# with default args.  later section of code \n';
    initMethodBody += '# initializes these variables.\n';
    initMethodBody += emitUtils.createDictLiteralAssignment(
        'self._committedContext.shareds',sharedDict);
    initMethodBody += '\n\n';            

    # globals
    globalsDict = {};
    for globalId in sorted(globalIdentifiersToDeclNodesDict.keys()):
        declNode = globalIdentifiersToDeclNodesDict[globalId];
        typeDeclNode = declNode.children[0]
        defaultVal = emitUtils.getDefaultValueFromDeclNode(declNode);

        # put some default values in for endpoint global variables.
        # after this, still initialize variables later below
        if typeDeclNode.external == None:
            sharedDict[ "'" + globalId + "'"] = defaultVal;
        else:
            sharedDict[ "'" + globalId + "'"] = "None";


    initMethodBody += '# emitting local copies of endpoint global variables\n';
    initMethodBody += '# with default args.  later section of code \n';
    initMethodBody += '# initializes these variables.\n';
    initMethodBody += emitUtils.createDictLiteralAssignment(
        'self._committedContext.endGlobals',sharedDict);
    initMethodBody += '\n\n';            

    # context should not have any sequence globals
    initMethodBody += '# committed context never has sequence globals in it.\n'
    initMethodBody += 'self._committedContext.seqGlobals = None;\n'
    

    # emit initialization of shared and endpoint global variables.
    initMethodBody += '\n# initialization of shared and global variables\n';
    initMethodBody += '# note that writing to _context implicitly writes to\n'
    initMethodBody += '# self._committedContext.\n';

    # handles shared
    initMethodBody += _emitInitSharedGlobalVariables(
        endpointName,sharedIdentifiersToDeclNodesDict,
        astRootNode,fdepDict,emitContext);
    # handles endpoint global
    initMethodBody += _emitInitSharedGlobalVariables(
        endpointName,globalIdentifiersToDeclNodesDict,
        astRootNode,fdepDict,emitContext);
    initMethodBody += '\n\n';


    # on create function (if it exists)
    if onCreateNode != None:
        # need to do reference counting setup for external variables, etc.

        oncreate_call = '\n# put the external object in the external store\n';

        extArgString = '';
        for extFuncArg in externalOnCreateArgumentNames:
            oncreate_call +='''
self._externalStore.incrementRefCountAddIfNoExist(
    self._endpointName,%s);
''' % extFuncArg;
            
            extArgString += extFuncArg + ',';

        oncreate_call += '\n# call oncreate function for remaining initialization \n'
        oncreate_call += '# first need to hold all the references that it could use.'
        oncreate_call += 'self._committedContext.holdExternalReferences('
        fdep = mainEmit._findFunctionDepFromFDepDict(ONCREATE_TOKEN,endpointName,fdepDict)
        if fdep == None:
            assert(False)
        
        touchedExternalVarNames = fdep.getTouchedExternals(fdepDict)

        external_vars = '['
        for touchedExternal in touchedExternalVarNames.keys():
            external_vars += "'" + touchedExternal + "',"
        external_vars += ']'
        oncreate_call += external_vars + ')\n'

        oncreate_call += '\n# actually make the call\n'
        
        funcCallHead = 'self.%s(' % _convertSrcFuncNameToInternal(ONCREATE_TOKEN);
        oncreate_call += funcCallHead

        # indent_str keeps track of how much we need to indent to align arguments
        indent_str = ''
        for count in range(0,len(funcCallHead)):
            indent_str += ' '

        # insert function arguments
        oncreate_call += '_Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED,\n'
        oncreate_call += indent_str + '1, '
        oncreate_call += '# note that this is just a dummy variable. \n'
        oncreate_call += indent_str + '   # act event should not be used within funciton\n'
        oncreate_call += indent_str + 'self._committedContext,'

        # actually perform call to internal oncreate
        for argName in onCreateArgumentNames:
            # before calling internal oncreate, need to change all
            # map/list user-supplied arguments over to _WaldoList and
            # _WaldoMap objects


            oncreate_call += '\n' + indent_str
            if _argIsNonExternalMap(onCreateNode,argName):
                oncreate_call +=  '_WaldoMap(' + argName + ',True)'
            elif _argIsNonExternalList(onCreateNode,argName):
                oncreate_call +=  '_WaldoList(' + argName + ',True)'
            else:
                oncreate_call += argName
                
            oncreate_call += ', # user-defined arg'
            
        oncreate_call += '\n' + indent_str + ');\n';
        oncreate_call += '''


# oncreate_call actually needs to commit the context.
# Although we assume that oncreate cannot be pre-empted, and
# therefore use _committedContext directly, we still need to
# commit it in case oncreate call makes any changes to
# external reference objects.
self._committedContext.commit()

# to release reference count I took on external argument
# passed in and to garbage collect any externals with no
# references.

_extInterfaceCleanup = _ExtInterfaceCleanup(
    [%s],self._externalStore,self._endpointName);
_extInterfaceCleanup.start();

''' % extArgString;


        initMethodBody += oncreate_call + '\n'
    
    else:
        initMethodBody += '# no oncreate function to call.\n';


    initMethod += emitUtils.indentString(initMethodBody,1);
    return initMethod;

def _getMessageFunctionNodes(endpointName,astRootNode):
    '''
    @returns{Array} --- return an array of MessageFuncNodeShared
    objects, containing all of the message receive and message send
    sequence functions for the endpoint named endpointName.  
    '''
    returner = [];
    msgSeqSectionNode = astRootNode.children[6];

    for msgSeqNode in msgSeqSectionNode.children:

        msgSeqNameNode = msgSeqNode.children[0];
        msgSeqName = msgSeqNameNode.value;
        
        seqGlobalsNode = msgSeqNode.children[1];
        seqFuncsNode = msgSeqNode.children[2];

        counter = 0;
        for msgFuncNode in seqFuncsNode.children:
            endpointIdNode = msgFuncNode.children[0];

            counter +=1;
            
            # means that this function is one of this endpoint's
            # functions
            if endpointIdNode.value == endpointName:
                nextToGetCalledNode = None;
                if counter < len(seqFuncsNode.children):
                    nextToGetCalledNode = seqFuncsNode.children[counter];
                    
                toAppend = _MessageFuncNodeShared(
                    seqGlobalsNode,msgFuncNode,
                    nextToGetCalledNode,msgSeqName,
                    msgSeqNode);
                
                returner.append(toAppend);
          
    return returner;

class _MessageFuncNodeShared(object):
    '''
    Used as a return value from message function nodes.  Essentially,
    for all message sequence send nodes, we want to also keep track of
    the sequence global node too so can initialize these variables at
    top of function.
    '''
    def __init__(self,seqGlobalNode,msgFuncNode,
                 nextToCallNode,sequenceName,msgSeqNode):
        
        self.seqGlobalNode = seqGlobalNode;
        self.msgFuncNode = msgFuncNode;
        self.msgSeqNode = msgSeqNode;
        
        # the node for the message sequence function that will succeed
        # msgFuncNode's call (or None) if last message in sequence.
        self.nextToCallNode = nextToCallNode;

        self.sequenceName = sequenceName;
        
    def emitMessageFunctionDefinition(
        self,endpointName,astRootNode,fdepDict,emitContext):
        '''
        Emits the definition of the message receieve or message send
        function node that this wraps
        '''
        # keep track of message sequence node so that when encounter
        # jump statements, can use the message sequence node to
        # determine where to jump to.
        emitContext.msgSequenceNode = self.msgSeqNode;
        emitContext.msgSeqFuncNode = self.msgFuncNode;

        
        if self.msgFuncNode.label== AST_MESSAGE_SEND_SEQUENCE_FUNCTION:
            return self._emitSend(endpointName,astRootNode,fdepDict,emitContext);
        elif self.msgFuncNode.label == AST_MESSAGE_RECEIVE_SEQUENCE_FUNCTION:
            return self._emitReceive(endpointName,astRootNode,fdepDict,emitContext);
        elif self.msgFuncNode.label == AST_ONCOMPLETE_FUNCTION:
            return self._emitOnComplete(endpointName,astRootNode,fdepDict,emitContext);
        else:
            errMsg = '\nBehram error: trying to emit a message function ';
            errMsg += 'that is not actually a message function.\n';
            print(errMsg);
            assert(False);

        emitContext.msgSequenceNode = None;
        emitContext.msgSeqFuncNode = None;
        
    def isOnComplete(self):
        return self.msgFuncNode.label == AST_ONCOMPLETE_FUNCTION;

    def _emitOnComplete(self,endpointName,astRootNode,fdepDict,emitContext):
        '''
        Should only be called whenseqGlobalNode is AST_ONCOMPLETE_FUNCTION.

        @returns {String}
        '''
        emitContext.inOnComplete();
        
        if self.msgFuncNode.label != AST_ONCOMPLETE_FUNCTION:
            assert(False);

        functionBodyNode = _getFuncBodyNodeFromFuncNode(self.msgFuncNode);    
        
        # oncomplete nodes should be labeled such that their
        # sliceAnnotationNames can be used as their method definitions.
        self.msgFuncNode._debugErrorIfHaveNoAnnotation('_emitOnComplete');

        returner = '';

        # note, if change oncomplete function name, must also change
        # it in specifyOnCompleteDict of onCompleteDict.py
        returner += ('def %s(self,_callType,_actEvent,_context):' %
                     self.msgFuncNode.sliceAnnotationName);
        returner += '\n';

        methodBody = r"""'''

@param{_Endpoint} self --- Unusual use of self: want to maintain the
emitting code for function bodies, which assumes that called from
within an _Enpdoint class, rather than called from external class.
Way that I am getting around this is to explicitly pass endpoint in as
first argument and naming that argument self.

@param{String} _callType ---

   _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED :
   means that anything that we return will not be set in
   return statement of context, but rather will just be
   returned.

   Cannot have _callType equal to FIRST_FROM_EXTERNAL call
   (because no external callers), nor can have _callType equal
   to resume from postpone because by the time we reach onComplete,
   we have made guarantee that will run to completion.

@param{_ActiveEvent object} _actEvent --- Must be non-None,
but other than that, does nothing.

@param{_Context object} _context --- Each function can operate
on endpoint global, sequence global, and shared variables.
These are all stored in this _context object.  Must be
non-None for message receive.
'''
#### DEBUG
if _callType != _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED:
    errMsg = '\nBehram error.  An oncomplete function was ';
    errMsg += 'called without an internally_called _callType.\n';
    print(errMsg);
    assert(False);

if _context == None:
    errMsg = '\nBehram error.  An oncomplete function was called ';
    errMsg += 'without a context.\n';
    print(errMsg);
    assert(False);
#### END DEBUG

# meat of oncomplete
""";

        for statementNode in functionBodyNode.children:
            methodBody += mainEmit.emit(
                endpointName,statementNode,fdepDict,emitContext);
            methodBody += '\n';
        if methodBody == '':
            methodBody += 'pass;\n';

        returner += emitUtils.indentString(methodBody,1);
        emitContext.outOfOnComplete();
        return returner;
        

            
    def _emitReceive(self,endpointName,astRootNode,fdepDict,emitContext):
        '''
        Should only be called when seqGlobalNode is
        AST_MESSAGE_RECEIVE_SEQUENCE_FUNCTION
        
        @returns {String}
        '''
        if self.msgFuncNode.label != AST_MESSAGE_RECEIVE_SEQUENCE_FUNCTION:
            assert(False);

        funcNameNode = self.msgFuncNode.children[1];
        funcName = funcNameNode.value;
        # do not expect any function arguments for message receive
        # function; funcArguments should just be [].
        funcArguments = _getArgumentNamesFromFuncNode(self.msgFuncNode);
        functionBodyNode = _getFuncBodyNodeFromFuncNode(self.msgFuncNode);    

        returner = '';
        returner += 'def %s (self, ' % _convertSrcFuncNameToInternal(funcName);
        # for argName in funcArguments:
        #     returner += argName + ', ';
        # takes no external arguments
        returner +=  '_callType,_actEvent,_context):\n'

        # header will be the same for all message sends
        receiveBody = r"""'''
@param{String} _callType ---

   _Endpoint._FUNCTION_ARGUMENT_CONTROL_FROM_MESSAGE :

   Cannot have _callType equal to FIRST_FROM_EXTERNAL or
   internal call (because no external callers), nor can have
   _callType equal to resume from postpone because by the time
   have a message receive, have made guarantee that will run
   to completion.

@param{_ActiveEvent object} _actEvent --- Must be non-None,
but other than that, does nothing.

@param{_Context object} _context --- Each function can operate
on endpoint global, sequence global, and shared variables.
These are all stored in this _context object.  Must be
non-None for message receive.
'''
#### DEBUG
if _callType != _Endpoint._FUNCTION_ARGUMENT_CONTROL_FROM_MESSAGE:
    errMsg = '\nBehram error.  A message receive function was ';
    errMsg += 'called without from message _callType.\n';
    print(errMsg);
    assert(False);

if _actEvent == None:
    errMsg = '\nBehram error.  A message receive function was ';
    errMsg += 'called without an active event.\n';
    print(errMsg);
    assert(False);

if _context == None:
    errMsg = '\nBehram error.  A message receive function was called ';
    errMsg += 'without a context.\n';
    print(errMsg);
    assert(False);
#### END DEBUG

# actual meat of the function.
""";

        # actually emit the body of the function
        for statementNode in functionBodyNode.children:
            receiveBody += mainEmit.emit(
                endpointName,statementNode,fdepDict,emitContext);
            receiveBody += '\n';

        receiveBody += self._msgSendSuffix(fdepDict);
        returner += emitUtils.indentString(receiveBody,1);
        return returner;



    def _emitSend(self,endpointName,astRootNode,fdepDict,emitContext):
        '''
        Should only be called when seqGlobalNode is a message send
        sequence function.

        @returns {String}
        '''
        if self.msgFuncNode.label != AST_MESSAGE_SEND_SEQUENCE_FUNCTION:
            assert(False);

        funcNameNode = self.msgFuncNode.children[1];
        funcName = funcNameNode.value;
        funcArguments = _getArgumentNamesFromFuncNode(self.msgFuncNode);
        functionBodyNode = _getFuncBodyNodeFromFuncNode(self.msgFuncNode);    

        returner = '';

        returner += 'def %s (self, ' % _convertSrcFuncNameToInternal(funcName);
        returner +=  '_callType,_actEvent,_context'
        for argName in funcArguments:
            # defaulting to none here in case function is called as a
            # result of a message.
            returner += ',' + argName + '=None ';
        returner += '):\n';


        # header will be the same for all message sends
        sendBody = r"""'''
@param{String} _callType ---
   _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED :
   means that anything that we return will not be set in
   return statement of context, but rather will just be
   returned.

   or

   _Endpoint._FUNCTION_ARGUMENT_CONTROL_FROM_MESSAGE : means that we
   jumped back to this function and that we should therefore
   not re-initialize all sequence variables


@param{_ActiveEvent object} _actEvent --- Must be non-None,
but other than that, does nothing.

@param{_Context object} _context --- Each function can operate
on endpoint global, sequence global, and shared variables.
These are all stored in this _context object.  Must be
non-None for message receive.
'''
#### DEBUG
if ((_callType != _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED) and
    (_callType != _Endpoint._FUNCTION_ARGUMENT_CONTROL_FROM_MESSAGE)):
    errMsg = '\nBehram error.  A message send function must be ';
    errMsg += 'called with an internally_called or message _callType.\n';
    print(errMsg);
    assert(False);

if _actEvent == None:
    errMsg = '\nBehram error.  A message send function was ';
    errMsg += 'called without an active event.\n';
    print(errMsg);
    assert(False);

if _context == None:
    errMsg = '\nBehram error.  A message send function was called ';
    errMsg += 'without a context.\n';
    print(errMsg);
    assert(False);
#### END DEBUG


if _callType == _Endpoint._FUNCTION_ARGUMENT_CONTROL_INTERNALLY_CALLED:
    # initialization of sequence global variables: specific to
    # message send functions.
"""

        initializationBody = '';

        # need to perform initializations of sequence global data
        for declNode in self.seqGlobalNode.children:
            initializationBody += mainEmit.emit(endpointName,declNode,fdepDict,emitContext);
            initializationBody += '\n';

        # need to put arguments into seqGlobals
        funcDeclArgListNode = self.msgFuncNode.children[2];
        for funcDeclArgNode in funcDeclArgListNode.children:
            nameNode = funcDeclArgNode.children[1];
            nameNode._debugErrorIfHaveNoAnnotation(
                '_emitSend');

            nameString = nameNode.value;
            annotationName = nameNode.sliceAnnotationName;
            initializationBody += "_context.seqGlobals['%s'] = %s;\n\n" % (annotationName,nameString);
            # gives something like _context.seqGlobals['8__someArg'] = someArg;

        if initializationBody == '':
            initializationBody += 'pass;\n';
        sendBody += emitUtils.indentString(initializationBody,1);
        
        
        # actually emit the body of the function
        sendBody += '\n# emitting body of send function.\n';
        for statementNode in functionBodyNode.children:
            sendBody += mainEmit.emit(endpointName,statementNode,fdepDict,emitContext);
            sendBody += '\n';
        
        sendBody += self._msgSendSuffix(fdepDict);
        returner += emitUtils.indentString(sendBody,1);
        return returner;
    
    def _msgSendSuffix(self,fdepDict):
        returner = '';

        # check whether this is the last message in the
        # sequence...have different semantics if it is: notify other
        # side that sequence is done, and send sequence complete
        # signal to waiting function node.
        if ((self.nextToCallNode == None) or
            (self.nextToCallNode.label == AST_ONCOMPLETE_FUNCTION)):
            returner += emitUtils.lastMessageSuffix(self.sequenceName);
        else:
            # what to send as control messsage for function so that it
            # calls next function in message sequence on its side.
            nextToCallEndpointIdentifierNode = self.nextToCallNode.children[0];
            nextToCallEndpointName = nextToCallEndpointIdentifierNode.value;
            nextToCallFuncNameNode = self.nextToCallNode.children[1];
            nextToCallFuncName = nextToCallFuncNameNode.value;

            nextFuncEventName = emitUtils.getFuncEventKey(
                nextToCallFuncName,nextToCallEndpointName,fdepDict);
            
            returner += emitUtils.nextMessageSuffix(
                nextFuncEventName,self.sequenceName);

        return returner;


def _getEndpointExternalsFromEndpointName(
    endpointName,astRootNode):
    '''
    @returns {dict} keys of dict are the identifiers that should
    use for each function and the values are simple boolean true.

    # creates something like
    #   {
    #      "''0__externalValue''" : True,
    #       ...
    #   }
    '''
    endpointNode = _getEndpointNodeFromEndpointName(endpointName,astRootNode);
    endpointBodyNode = endpointNode.children[1];
    endpointGlobalsNode = endpointBodyNode.children[0];

    returner = {};
    for declNode in endpointGlobalsNode.children:
        if declNode.external == True:
            declIdNode = declNode.children[1];
            declIdNode._debugErrorIfHaveNoAnnotation(
                '_getEndpointExternalsFromEndpointName');

            returner ["'" + declIdNode.sliceAnnotationName + "'"] = str(True);

    return returner;
    
def _getOnCreateNode(endpointName,astRootNode):
    '''
    @return {None or AstNode} --- None if endpoint named endpointName
    does not have a node, AstNode if it does.
    '''
    functionSectionNode = _getFunctionSectionNode(
        endpointName,astRootNode);

    # find the oncreate function
    for funcNode in functionSectionNode.children:
        if funcNode.label == AST_ONCREATE_FUNCTION:
            # actually emit all function text for node.
            return funcNode;

    return None;

def _getExternalArgumentNamesFromFuncNode(funcNode):
    '''
    @param {AstNode} funcNode --- for private, public, oncreate,
    message receive, and message send functions.

    @returns {Array} --- Each element is a string representing the
    name of the external argument that the user passed in.
    '''
    argNodeIndex = _getArgumentIndexFromFuncNodeLabel(funcNode.label);

    if argNodeIndex == None:
        assert(False);

    returner = [];
    funcDeclArgListNode = funcNode.children[argNodeIndex];
    for funcDeclArgNode in funcDeclArgListNode.children:
        if funcDeclArgNode.external == True:
            nameNode = funcDeclArgNode.children[1];
            returner.append(nameNode.value);

    return returner;


def _getReturnTypeIndexFromFuncNodeLabel(label):
    return_node_index = None
    if label == AST_PUBLIC_FUNCTION:
        return_node_index = 1
    elif label == AST_PRIVATE_FUNCTION:
        return_node_index = 1
    else:
        err_msg = '\nBehram error: cannot request a return type '
        err_msg += 'node for non-public or non-private node.\n'
        print err_msg
        assert (False)
        
    return return_node_index

def _getArgumentIndexFromFuncNodeLabel(label):
    argNodeIndex = None;
    if label == AST_PUBLIC_FUNCTION:
        argNodeIndex = 2;
    elif label == AST_PRIVATE_FUNCTION:
        argNodeIndex = 2;
    elif label == AST_ONCREATE_FUNCTION:
        argNodeIndex = 1;
    elif label == AST_MESSAGE_SEND_SEQUENCE_FUNCTION:
        argNodeIndex = 2;
    else:
        errMsg = '\nBehram error: cannot call getArgIndFromFunc on ';
        errMsg += 'nodes that are not function nodes.\n';
        print(errMsg);
        assert(False);

    return argNodeIndex;


def _getArgumentNamesFromFuncNode(funcNode):
    '''
    @param {AstNode} funcNode --- for private, public, oncreate,
    message receive, and message send functions.

    @returns {Array} --- Each element is a string representing the
    name of the argument that the user passed in.
    '''
    if funcNode.label == AST_MESSAGE_RECEIVE_SEQUENCE_FUNCTION:
        return [];

    argNodeIndex = _getArgumentIndexFromFuncNodeLabel(funcNode.label);
    if argNodeIndex == None:
        errMsg = '\nBehram error: cannot call argumentnamesfromfuncnode on ';
        errMsg += 'nodes that are not function nodes.\n';
        print(errMsg);
        assert(False);

    returner = [];
    funcDeclArgListNode = funcNode.children[argNodeIndex];
    for funcDeclArgNode in funcDeclArgListNode.children:
        nameNode = funcDeclArgNode.children[1];
        name = nameNode.value;
        returner.append(name);
        
    return returner;

def _getFuncBodyNodeFromFuncNode(funcNode):
    '''
    @param {AstNode} funcNode --- for private, public, oncreate,
    message receive, and message send functions

    @returns{AstNode} --- The ast node containing the function's body.
    '''
    bodyNodeIndex = None;
    if funcNode.label == AST_PUBLIC_FUNCTION:
        bodyNodeIndex = 3;
    elif funcNode.label == AST_PRIVATE_FUNCTION:
        bodyNodeIndex = 3;
    elif funcNode.label == AST_ONCREATE_FUNCTION:
        bodyNodeIndex = 2;
    elif funcNode.label == AST_MESSAGE_SEND_SEQUENCE_FUNCTION:
        bodyNodeIndex = 3;
    elif funcNode.label == AST_MESSAGE_RECEIVE_SEQUENCE_FUNCTION:
        bodyNodeIndex = 2;
    elif funcNode.label == AST_ONCOMPLETE_FUNCTION:
        bodyNodeIndex = 2;
    else:
        errMsg = '\nBehram error: cannot get funcbodynode from ';
        errMsg += 'nodes that are not function nodes.\n';
        print(errMsg);
        assert(False);

    return funcNode.children[bodyNodeIndex];

    

def _getFunctionSectionNode(endpointName,astRootNode):
    endpointNode = _getEndpointNodeFromEndpointName(
        endpointName,astRootNode);

    bodySectionNode = endpointNode.children[1];
    functionSectionNode = bodySectionNode.children[1];
    return functionSectionNode;
    

def _emitInitSharedGlobalVariables(
    endpointName,idsToDeclNodesDict,astRootNode,fdepDict,emitContext):
    '''
    Inside of init function of each endpoint class, need to initialize
    shared variables and endpoint global variables with their initial
    values.
    '''
    returner = '';
    for _id in idsToDeclNodesDict:
        declNode = idsToDeclNodesDict[_id];
        typeNode = declNode.children[0]
        returner += mainEmit.emit(endpointName,declNode,fdepDict,emitContext);
        returner += '\n';
    return returner;
    
def _getSharedIdsToDeclNodesDict(astRoot):
    '''
    @returns {dict} --- keys are identifiers (annotated by slicer
    code) for shared variables and values are the declaration nodes.
    '''
    returner = {};
    
    sharedSectionNode = astRoot.children[3];
    for annotatedDeclarationNode in sharedSectionNode.children:
        # have an annotatedDeclarationNode for each shared variable.
        identifierNode = annotatedDeclarationNode.children[2];
        identifierNode._debugErrorIfHaveNoAnnotation('_getSharedIdentifiersToTypeDict');
        returner[identifierNode.sliceAnnotationName] = annotatedDeclarationNode;

    return returner;


def _getEndpointNodeFromEndpointName(endpointName,astRootNode):
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
        errMsg += 'get endpoint node from.\n';
        print(errMsg);
        assert(False);
        
    return toCheckEndpointNode;


def _getEndpointIdsToDeclNodesDict(endpointName,astRootNode):
    '''
    @returns {dict} --- Keys are identifiers for each of the values,
    which are endpoint global declaration nodes.
    '''
    endpointNode = _getEndpointNodeFromEndpointName(endpointName,astRootNode);

    returner = {};
    if endpointNode.label != AST_ENDPOINT:
        errMsg = '\nBehram error: Error _getEndpointVariableIdentifiersToTypeDict ';
        errMsg += 'expected an ast node labeled as an endpoint.\n';
        print(errMsg);
        assert(False);

    endpointBodyNode = endpointNode.children[1];
    endpointGlobalsSectionNode = endpointBodyNode.children[0];

    for declNode in endpointGlobalsSectionNode.children:
        identifierNode = declNode.children[1];
        identifierNode._debugErrorIfHaveNoAnnotation(
            '_getEndpointVariableIdentifiersFromEndpointNode');
        returner[identifierNode.sliceAnnotationName] = declNode;
        
    return returner;



def _getEndpointFunctionNamesFromEndpointName(
    endpointName,astRootNode,functionDepsDict):
    '''
    @param {String} endpointName
    @param {AstNode} astRootNode

    @return {dict} --- keys of dict are the identifiers that should
    use for each function and the values are the internal names that
    the function takes in the endpoint class

    # creates something like
    #   {
    #      "'Ping_-_-_incPing'" : "'_incPing'",
    #       ...
    #   }
    
    '''
    returner = {};
    for fdepKey in sorted(functionDepsDict.keys()):
        fdep = functionDepsDict[fdepKey];

        if fdep.endpointName != endpointName:
            continue;

        # means that this function occurrs within this endpoint.  list it.
        returner["'" + fdep.funcName + "'"] = "'" + _convertSrcFuncNameToInternal(fdep.srcFuncName) + "'";
        
    return returner;


