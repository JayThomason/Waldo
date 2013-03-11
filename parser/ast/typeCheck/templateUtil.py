#!/usr/bin/env python

import sys;
import os;

from parser.ast.astLabels import *
import json


'''
Almost all of these utility functions are built to allow access to,
type check, and construct the three templated types that waldo
supports:
  * function objects
  * lists
  * maps
'''


JSON_TYPE_FIELD = 'Type';
JSON_FUNC_RETURNS_FIELD = 'Returns';
JSON_FUNC_IN_FIELD = 'In';

JSON_LIST_ELEMENT_TYPE_FIELD = 'ElementType';

JSON_MAP_FROM_TYPE_FIELD = 'From';
JSON_MAP_TO_TYPE_FIELD = 'To';
JSON_TUPLE_TYPE_FIELD = 'Tuple'


JSON_STRUCT_FIELDS_DICT = 'StructFields'
JSON_STRUCT_FIELDS_NAME = 'StructName'

# There is no real wildcard type in Waldo.  This is just used to make
# adding features easier.  For instance, with calling functions on
# endpoint objects, instead of having to type check the endpoint that
# we're using, we can just assign into an endpoint function.
WILDCARD_TYPE = 'Wildcard'


def create_struct_type(struct_name,struct_field_tuples):
    '''
    @param {String} struct_name --- The name of the user-defined
    struct.

    @param{Array} struct_field_tuples --- Each element of the array is
    a two-tuple.  The first element is the name of the field and the
    second is the type of that element field.  
    '''
    struct_type = {
        JSON_TYPE_FIELD: TYPE_STRUCT,
        JSON_STRUCT_FIELDS_DICT: {},
        JSON_STRUCT_FIELDS_NAME: struct_name
        }

    for single_field in struct_field_tuples:
        field_name = single_field[0]
        field_type = single_field[1]

        # add field type to fields dict
        struct_type[JSON_STRUCT_FIELDS_DICT][field_name] = field_type

    return struct_type


def is_wildcard_type(type_dict):
    return type_dict[JSON_TYPE_FIELD] == WILDCARD_TYPE

def create_wildcard_type():
    to_return = {
        JSON_TYPE_FIELD: WILDCARD_TYPE
        }
    return to_return
    

def get_struct_name_from_type(struct_type_dict):
    if not is_struct(struct_type_dict):
        err_msg = '\nBehram error.  Attempting to get the struct name '
        err_msg += 'for a type that is not a struct.'
        print err_msg
        assert(False)
        
    return struct_type_dict[JSON_STRUCT_FIELDS_NAME]

def get_struct_field_type(field_name,struct_type_dict):
    '''
    @param{String} field_name --- The name of the field that we want
    to know the type of in struct_type_dict
    
    @param{dict type} struct_type_dict --- Throws error if is not a struct
    type.

    @returns {None or type dict} --- Returns None if the field did not
    exist within the struct.  Returns the type dict associated with
    that field otherwise.
    '''
    if not is_struct(struct_type_dict):
        err_msg = '\nBehram error: get_struct_field_type requires '
        err_msg += 'a struct type dict.\n'
        print err_msg
        assert(False)

    struct_fields_dict = struct_type_dict[JSON_STRUCT_FIELDS_DICT]
    return struct_fields_dict.get(field_name,None)


def is_endpoint(dict_type):
    _assert_if_not_dict(dict_type,'is_endpoint')
    to_return = dict_type[JSON_TYPE_FIELD] == TYPE_ENDPOINT
    return to_return

def is_struct(dict_type):
    _assert_if_not_dict(dict_type,'is_struct')
    return dict_type[JSON_TYPE_FIELD] == TYPE_STRUCT

def is_true_false(dict_type):
    _assert_if_not_dict(dict_type,'is_true_false')
    return dict_type[JSON_TYPE_FIELD] == TYPE_BOOL

def is_text(dict_type):
    _assert_if_not_dict(dict_type,'is_text')
    return dict_type[JSON_TYPE_FIELD] == TYPE_STRING

def is_number(dict_type):
    _assert_if_not_dict(dict_type,'is_number')
    return dict_type[JSON_TYPE_FIELD] == TYPE_NUMBER

def is_nothing_type(dict_type):
    _assert_if_not_dict(dict_type,'is_nothing_type')
    return dict_type[JSON_TYPE_FIELD] == TYPE_NOTHING
    
def is_empty_map(dict_type):
    _assert_if_not_dict(dict_type,'is_empty_map')
    return dict_type[JSON_TYPE_FIELD] == EMPTY_MAP_SENTINEL

def is_empty_list(dict_type):
    _assert_if_not_dict(dict_type,'is_empty_list')
    return dict_type[JSON_TYPE_FIELD] == EMPTY_LIST_SENTINEL

def is_returned_tuple(dict_type):
    _assert_if_not_dict(dict_type,'is_returned_tuple')
    return dict_type[JSON_TYPE_FIELD] == TYPE_RETURNED_TUPLE

def is_function_call_return_type_dict(type_dict):
    '''
    @returns {bool} True if this type dict corresponds to a function
    call.  False otherwise.

    A non-function call type dict has structure
    {
      Type: { Type: Number}
    }
    
    Ie, types will either point at strings or maps.  In contrast,
    function call return type dicts will have a type that points to an
    array like that seen in the comment of @see
    get_type_array_from_func_call_returned_tuple_type.
    '''
    return isinstance(type_dict[JSON_TYPE_FIELD], list)


def get_type_array_from_func_call_returned_tuple_type(
    func_call_return_type):
    '''
    @param {dict} func_call_return_type

    A function call should have a .type field generated from
    generate_returned_tuple_type that looks like this:

    {
      'Type': {
          'Type': [ {'Type': 'Number'}, ...]
          }
    }
      
    This helper function just strips off the outermost map and returns
    the array of return types when call a function.
    '''
    return func_call_return_type[JSON_TYPE_FIELD]


def get_single_type_if_func_call_reg_type(type_dict):
    '''
    A function call has the following type dict structure:
       {
          Type: [
                  {
                      Type: Number
                  },
                  {
                      Type: Text
                  },
                  ...
                ]
       }
       
    however, we want to be able to make calls, such as

    if (func_call())
        <do something>

    In this case, we don't want the entire tuple type-dict, but just
    the first type that the function call returns.

    This function takes in any type dict (of a function call or not).
    It returns the tuple (a,b)

        {type_dict} a: 
        {bool} b: 
    
    If type_dict is the type dict for a non-function call, then:

       a: type_dict
       b: False

    If type_dict is the type dict for a funciton call, then:
       a: type_dict for first return type

       b: True if there are more return types after, False otherwise.
    '''
    if not is_function_call_return_type_dict(type_dict):
        return type_dict,False

    type_dict_array = get_type_array_from_func_call_returned_tuple_type(
        type_dict)

    not_just_one_return_type_bool = True
    if len(type_dict_array) == 1:
        not_just_one_return_type_bool = False

    # zero index should always exist.  Even if function returns void,
    # type array should still contain None.  (I think.)
    return type_dict_array[0], not_just_one_return_type_bool


    

def generate_returned_tuple_type(tuple_element_list):
    '''
    Each one of these should themselves be a type dict.
    '''
    to_return = {}
    to_return[JSON_TYPE_FIELD] = TYPE_RETURNED_TUPLE
    to_return[JSON_TUPLE_TYPE_FIELD] = []
    for item in tuple_element_list:
        to_return[JSON_TUPLE_TYPE_FIELD].append(item)
    
    return to_return
    

def _assert_if_not_dict(to_check,caller):
    '''
    Asserts false if to_check is not a dict.

    caller should be a string, with the name of the function that
    called the check.
    '''
    if not isinstance(to_check,dict):
        err_msg = 'Berham error.  Passed in an incorrect '
        err_msg += 'data type to _assert_if_not_dict in '
        err_msg += caller + '.\n  Passed in: '
        err_msg += repr(to_check)
        err_msg += '\n\n'
        print err_msg
        assert(False)
        

def generate_type_as_dict(type_string):
    '''
    The .type fields of all nodes should be dicts with 'TYPE'
    specified in them.

    This takes one type and wraps it in another.
    '''

    return {
        JSON_TYPE_FIELD: type_string
        }


def dict_type_to_str(dict_type):
    '''
    @param {dict} dict_type 
    Used for printing error messages.
    '''
    if not isinstance(dict_type,dict):
        err_msg = '\nBehram error when converting type to string. '
        err_msg += 'Expected a dict.  But instead, got '
        err_msg += repr(dict_type)
        err_msg += '\n'
        print err_msg
        assert(False)

    return '\n' + json.dumps(dict_type, sort_keys=True,indent=2) + '\n'


def isValueType(type_field):
    '''
    Text, TrueFalse, and Number are all value types.  Everything else is not
    '''

    return is_true_false(type_field) or is_text(type_field) or is_number(type_field)


def isFunctionType(typeLabel):
    '''
    Nodes can have many different type labels.  Some are specified by
    strings (mostly nodes with basic types, eg. Number, String, etc.).

    Nodes for user-defined function types do not just have one
    annotation, but rather a json-ized type.  To check if a node's
    label is one of these user-defined function types, we check to
    exclude all of the other types it could be.

    Returns true if it is a user-defined function type, false otherwise.
    '''
    return (is_basic_function_type(typeLabel) or
            is_endpoint_function_type(typeLabel))

def is_basic_function_type(typeLabel):
    return typeLabel[JSON_TYPE_FIELD] == TYPE_FUNCTION
def is_endpoint_function_type(typeLabel):
    return typeLabel[JSON_TYPE_FIELD] == TYPE_ENDPOINT_FUNCTION_CALL

def isListType(typeLabel):
    '''
    Automatically handles case of EMPTY_LIST_SENTINEL
    '''
    if is_empty_list(typeLabel):
        return True
    
    return typeLabel[JSON_TYPE_FIELD] == TYPE_LIST


def getListValueType(node_type):
    '''
    @param {type dict} node_type -- an ast node's .type field.
    
    Note: presupposes that this is a list.  otherwise asserts out.
    similarly, user must ensure that node_type is not
    EMPTY_LIST_SENTINEL.
    '''
    if not isListType(node_type):
        errMsg = '\nBehram error.  Asking for list value type ';
        errMsg += 'of non-list.\n';
        print(errMsg);
        assert(False);

    if is_empty_list(node_type):
        errMsg = '\nBehram error.  Cannot call getListValueType on ';
        errMsg += 'an empty list.  Should have checked this condition ';
        errMsg += 'before calling into function.\n';
        print(errMsg);
        assert(False);

    return node_type[JSON_LIST_ELEMENT_TYPE_FIELD]


def getMapIndexType(node_type):
    '''
    @param {type dict} node_type --- an ast node's .type field.
    
    Note: should not put in EMPTY_MAP_SENTINEL for typeLabel.  User
    should pre-check for this.
    '''
    if not isMapType(node_type):
        print('\n\n');
        print('Behram error, requested to get index type from non-map\n');
        print('\n\n');
        assert(False);

    if is_empty_map(node_type):
        errMsg = '\nBehram error.  Cannot call getMapIndexType on ';
        errMsg += 'an empty map.  Should have checked this condition ';
        errMsg += 'before calling into function.\n';
        print(errMsg);
        assert(False);

    return node_type[JSON_MAP_FROM_TYPE_FIELD]


def getMapValueType(node_type):
    '''
    @param {type dict} node_type
    '''
    # node_type = node.type;
    if not isMapType(node_type):
        print('\n\n');
        print('Behram error, requested to get value type from non-map\n');
        print('\n\n');
        assert(False);

    if is_empty_map(node_type):
        errMsg = '\nBehram error.  Cannot call getMapValueType on ';
        errMsg += 'an empty map.  Should have checked this condition ';
        errMsg += 'before calling into function.\n';
        print(errMsg);
        assert(False);

    return node_type[JSON_MAP_TO_TYPE_FIELD]


def isMapType(typeLabel):
    '''
    Automatically handles case of EMPTY_MAP_SENTINEL
    '''
    if is_empty_map(typeLabel):
        return True
    
    return typeLabel[JSON_TYPE_FIELD] == TYPE_MAP


def isTemplatedType(typeLabel):
    '''
    @returns{bool} True if it's a function or list type, false otherwise.
    '''
    return (isMapType(typeLabel) or
            isListType(typeLabel) or
            isFunctionType(typeLabel))


def bothLists(a,b):
    return isListType(a) and isListType(b);

def bothMaps(a,b):
    return isMapType(a) and isMapType(b);

def moreSpecificListMapType(typeA,typeB):
    '''
    @param {String} typeA --- string-ified version of json list/map type.
    @param {String} typeB --- string-ified version of json list/map type.

    @returns{String} typeA or typeB, depending on which is more
    specific.

    In particular, if
       typeA = []
       and
       typeB = [Number]
    will return typeB
    Similarly, if
       typeA = [ [] ]
       and
       typeB = [ [TrueFalse] ]
    will return typeB

    If both typeA and typeB are equally specific but conflict, returns
    either.  For example, if 
       typeA = [ Number ]
       and
       typeB = [ TrueFalse ]
    could return either typeA or typeB.
    '''

    if is_empty_list(typeA) or is_empty_map(typeA):
        return typeB;

    if is_empty_list(typeB) or is_empty_map(typeB):
        return typeA;

    twoMaps = False;
    if bothLists(typeA,typeB):
        # grab the types of elements for each list.
        valueTypeA = get_list_value_type(typeA)
        valueTypeB = get_list_value_type(typeB)

        # can just set these to any non-sentinel value
        indexTypeA = '';
        indexTypeB = '';
        
    elif bothMaps(typeA,typeB):
        twoMaps = True;
        valueTypeA = getMapValueType(typeA)
        valueTypeB = getMapValueType(typeB)

        indexTypeA = getMapIndexType(typeA)
        indexTypeB = getMapIndexType(typeB)
    else:
        # otherwise, type mismatch: return one or the other.
        return typeA;
        
    if is_empty_list(valueTypeA) or is_empty_map(valueTypeA):
        # means that typeB is at least as specific
        return typeB;

    if is_empty_list(valueTypeB) or is_empty_map(valueTypeB):
        # means that typeA is at least as specific        
        return typeA;

    if indexTypeA != indexTypeB:
        # mismatch, return either
        return typeA;
        
    if ( ((not isListType(valueTypeA) ) and
          (not isMapType(valueTypeA) ))
         
          or
         
        ((not isListType(valueTypeB) ) and
          (not isMapType(valueTypeB) ))):
        # if one or both are not lists or maps, that means that we've reached
        # the maximum comparison depth and we cannot get more
        # specific, so just return one or the other.
        return typeA;

    
    # each element itself is a list or a map
    recursionResult = moreSpecificListMapType(
        valueTypeA,valueTypeB)


    # must rebuild surrounding list type signature to match typeA or
    # typeB.
    if twoMaps:
        to_return = buildMapTypeSignatureFromTypeName(indexTypeA,recursionResult);
    else:
        to_return = buildListTypeSignatureFromTypeName(recursionResult);
        
    return to_return


def buildListTypeSignatureFromTypeName(node_type):
    '''
    @param {type dict} node_type....or EMPTY_LIST/EMPTY_MAP
    '''
    return {
        JSON_TYPE_FIELD: TYPE_LIST,
        JSON_LIST_ELEMENT_TYPE_FIELD: node_type
        };

def create_empty_list_type():
    return buildListTypeSignatureFromTypeName(EMPTY_LIST)


def buildListTypeSignature(node, progText,typeStack):
    elementTypeNode = node.children[0];
    elementTypeNode.typeCheck(progText,typeStack);
    elementType = elementTypeNode.type;
    return buildListTypeSignatureFromTypeName(elementType);



def buildMapTypeSignatureFromTypeNames(fromType,toType):
    '''
    @param {type dict} fromType
    @param {type dict} toType
    '''
    return {
        JSON_TYPE_FIELD: TYPE_MAP,
        JSON_MAP_FROM_TYPE_FIELD: fromType,
        JSON_MAP_TO_TYPE_FIELD: toType
        };

def getMapIndexType(node_type):
    '''
    @param {type dict} node_type
    
    If node_type is not for a map or for an empty map, assert out.
    '''
    if not isMapType(node_type):
        err_msg = '\nBehram error: trying to get the '
        err_msg += 'index for a non-map type.\n'
        print(err_msg)
        assert(False)

    if is_empty_map(node_type):
        err_msg = '\nBehram error.  Trying to get index type for '
        err_msg += 'empty map.\n'
        print(err_msg)
        assert(False)

    return node_type[JSON_MAP_FROM_TYPE_FIELD];



def buildMapTypeSignature(node,progText,typeStack):
    '''
    @returns 3-tuple: (a,b,c)

    a: {type dict} --- The actual type constructed
    
    b: {String or None} --- None if no error.  If there is an error,
       this text gives the error message.
    
    b: {list of ast nodes or None} --- None if no error.  Otherwise,
       returns the list of ast nodes that caused the error.
    '''
    fromTypeNode = node.children[0];
    fromTypeNode.typeCheck(progText,typeStack);
    toTypeNode = node.children[1];
    toTypeNode.typeCheck(progText,typeStack);

    fromType = fromTypeNode.type;

    errMsg = None;
    errNodeList = None;
    if not isValueType(fromType):
        # you can only map from Text,TrueFale,or Number to another value.
        errMsg = '\nError declaring function.  A map must map from a TrueFalse, ';
        errMsg += 'Text, or Number to any other type.  You are mapping from ';
        errMsg += 'a non-value type: ' + dict_type_to_str(fromType) + '.\n';

        errNodeList = [node,fromTypeNode];

    toType = toTypeNode.type
    return (buildMapTypeSignatureFromTypeNames(fromType,toType),
            errMsg,
            errNodeList)


def build_endpoint_func_type_signature(node,prog_text,type_stack):
    ### FIXME: need to support type checking for more complicated
    ### endpoint function calls
    to_return = {};
    to_return[JSON_TYPE_FIELD] = TYPE_ENDPOINT_FUNCTION_CALL
    to_return[JSON_FUNC_IN_FIELD] = []
    to_return[JSON_FUNC_RETURNS_FIELD] =  create_wildcard_type()

    return to_return

def buildFuncTypeSignature(node,progText,typeStack):
    '''
    @see createJsonType of FuncMatchObject in
    astTypeCheckStack.py....needs to be consistent between both.
    
    @param {AstNode} node --- Has value of FUNCTION_TYPE and type of
    AST_TYPE.  (Similar to the node that is generated for each type.)
    For instance, when declare

    Function (In: TrueFalse; Returns: Nothing) a;

    The node corresponds to the node generated from

    Function (In: TrueFalse; Returns: Nothing)


    @returns {dictionary}.  For the above example, dictionary would look like this:

    {
       Type: 'Function',
       In: [ { Type: 'TrueFalse'} ],
       Returns: [{ Type: 'Nothing'}] # this is a list so that can return tuples
    }
    '''
    returner = {};
    returner[JSON_TYPE_FIELD] = TYPE_FUNCTION;


    ##### HANDLE INPUT ARGS #####
    inArgNode = node.children[0];
    inputTypes = [];
    if (inArgNode.label != AST_EMPTY):
        # means that we have a node of type typelist.  each of its
        # children should be an independent type.
        for typeNode in inArgNode.children:
            
            typeNode.typeCheck(progText,typeStack);

            toAppend = {
                JSON_TYPE_FIELD: typeNode.type
                };
            inputTypes.append(toAppend);
            
    returner[JSON_FUNC_IN_FIELD] = inputTypes;

    ##### HANDLE OUTPUT ARGS #####
    outArgNode = node.children[1];
    outArgNode.typeCheck(progText,typeStack);
    
    returner[JSON_FUNC_RETURNS_FIELD] = {
        JSON_TYPE_FIELD: outArgNode.type
        };
        
    return returner;

