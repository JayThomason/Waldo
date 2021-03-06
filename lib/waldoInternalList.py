import waldoReferenceContainerBase
import util
import waldoReferenceBase
import waldoExecutingEvent

class InternalList(waldoReferenceContainerBase._ReferenceContainer):

    def __init__(self,host_uuid,peered,init_val):
        waldoReferenceContainerBase._ReferenceContainer.__init__(
            self,host_uuid,peered,init_val,_InternalListVersion(),
            _InternalListDirtyMapElement)
    
    def add_key(self,invalid_listener,key,new_val):
        util.logger_assert('Cannot call add_key on a list')

    def get_keys(self,invalid_listener):
        util.logger_assert('Cannot call get_keys on a list')
        
    @staticmethod
    def var_type():
        return 'internal list'

    def de_waldoify(self,invalid_listener):
        '''
        @see _ReferenceBase.de_waldoify
        '''
        internal_len = self.get_len(invalid_listener)
        to_return = []
        for index in range(0, internal_len):
            val = self.get_val_on_key(invalid_listener,index)
            de_waldoed_val = waldoExecutingEvent.de_waldoify(
                val, invalid_listener)
            
            to_return.append(de_waldoed_val)
            
        return to_return

    def contains_val_called(self,invalid_listener,val):
        '''
        Run through internal list, check if any element in the list is
        equal to val.  (Note == will only work with value types.)
        '''
        found = False
        
        self._lock()
        self._add_invalid_listener(invalid_listener)
        dirty_elem = self._dirty_map[invalid_listener.uuid]
        # essentially, just iterate through each element of list
        # looking for a matching val.
        for i in range(0,dirty_elem.get_len()):
            if dirty_elem.get_val_on_key(i) == val:
                found=True
                break
        self._unlock()

        return found

    def insert_into(self,invalid_listener, index, val):
        # this will get overwritten later.  for now, just append some
        # val
        
        self.append_val(invalid_listener,val)

        len_list = self.get_len(invalid_listener)
        for i in range(len_list-1,index,-1):
            self.write_val_on_key(
                invalid_listener,
                i,self.get_val_on_key(invalid_listener,i-1))
            
        self.write_val_on_key(invalid_listener,index,val)
        
    
    def contains_key(self,invalid_listener, key):
        util.logger_assert(
            'Cannot call contains_key on list')
        
    def append_val(self,invalid_listener,new_val):
        '''
        When we append, we insert at the end of the list.
        Changes contains, len, keys.
        '''
        self._lock()
        self._add_invalid_listener(invalid_listener)
        dirty_elem = self._dirty_map[invalid_listener.uuid]
        dirty_elem.append_val(new_val,invalid_listener,self.peered)
        if self.peered:
            invalid_listener.add_peered_modified()        
        self._unlock()

    def copy_if_peered(self,invalid_listener):
        '''
        @see waldoReferenceContainerBase._ReferenceContainer
        '''
        if not self.peered:
            return self

        return self.copy(invalid_listener,False)

    def copy(self,invalid_listener,peered):
        # will be used as initial_val when constructing copied
        # InternalMap that we return.
        new_internal_val = []
        
        # a peered internal map may point to values or it may point to
        # _ReferenceContainers.  (It may not point to non
        # _ReferenceContainer _WaldoObjects because we disallow
        # externals as value types for maps and lists.)
        self._lock()
        val_to_copy = self.val
        self_to_copy = True
        if invalid_listener.uuid in self._dirty_map:
            self_to_copy = False
            val_to_copy = self._dirty_map[invalid_listener.uuid].val
            
        # if copying from internal: stay within the lock so that
        # nothing else can write to internal while we are.
        if not self_to_copy:
            self._unlock()

        for to_copy in val_to_copy:
            # if it's not a _ReferenceContainer, then it must just
            # have a value type.  (See comment after
            # new_internal_val.)
            if isinstance(
                to_copy,waldoReferenceContainerBase._ReferenceContainer):
                to_copy = to_copy.copy(invalid_listener,peered)

            elif isinstance(
                to_copy,waldoReferenceBase._ReferenceBase):

                if to_copy.is_value_type():
                    to_copy = to_copy.get_val(invalid_listener)
                else:
                    to_copy = to_copy.copy(invalid_listener,peered)
                
            new_internal_val.append(to_copy)
            
        if self_to_copy:
            self._unlock()

        return InternalList(self.host_uuid,peered,new_internal_val)


class _InternalListDirtyMapElement(
    waldoReferenceContainerBase._ReferenceContainerDirtyMapElement):    

    def add_key(self,key,new_val,invalid_listener):
        util.logger_assert(
            'Cannot call add_key on a list')

    def del_key(self,key):
        self.version_obj.del_key_list(key,len(self.val))
        del self.val[key]
        
    def append_val(self,new_val,invalid_listener,peered):
        # adding key at end.
        self.version_obj.add_key(len(self.val))

        # if we are peered, then we want to assign into ourselves a
        # copy of the object, not the object itself.  This will only
        # be a problem for container types.  Non-container types
        # already have the semantics that they will be copied on read.
        # (And we throw an error if a peered variable has a container
        # with externals inside of it.)
        if peered:
            if isinstance(
                new_val,waldoReferenceContainerBase._ReferenceContainer):
                new_val = new_val.copy(invalid_listener,True)

            elif isinstance(
                new_val,waldoReferenceBase._ReferenceBase):
                
                if new_val.is_value_type():
                    new_val = new_val.get_val(invalid_listener)
                else:
                    new_val = new_val.copy(invalid_listener,True)

        self.val.append(new_val)

        
class _InternalListVersion(
    waldoReferenceContainerBase._ReferenceContainerVersion):
    
    def del_key(self,to_del):
        util.logger_assert(
            'Cannot call del_key on list.  Use del_key_list instead.')

    def copy(self):
        '''
        @see _ReferenceContainerVersion.copy
        '''
        copy = _InternalListVersion()
        copy.commit_num = self.commit_num
        return copy

    def del_key_list(self,del_index,length_of_list_before_del):
        '''
        When we delete an element:
          * add a delete on del_index
          
          * make a write from all elements from del_index until
            length_of_list_before_del - 1.  This is because when you
            delete a value from the middle of a list all the other
            values shift downwards.
        '''

        self.deleted_keys[del_index] = self.commit_num

        for shifted_write_index in range(del_index,length_of_list_before_del):
            self.deleted_keys[shifted_write_index] = self.commit_num
        
        
