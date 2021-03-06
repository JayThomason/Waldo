#!/usr/bin/env python

from two_sided_modify_peer_check_update_test_v4 import Modifier
from two_sided_modify_peer_check_update_test_v4 import DataReader

import sys,os
base_dir = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '..','..')
sys.path.append(base_dir)
from lib import Waldo

'''
Tests that changes to a peered type on one side get updated to partner
side.
'''

def run_test():
    modifier,data_reader = Waldo.same_host_create(Modifier).same_host_create(DataReader)

    # check peered value is initialized properly
    if modifier.read_peered_num() != 22:
        print '\nErr: incorrect modifier initial val of peered num'
        return False
    
    if data_reader.read_peered_num() != 22:
        print '\nErr: incorrect data reader initial val of peered num'
        return False

    # check modifier can increment
    if modifier.increment_peered_num() != 23:
        print '\nErr: incorrect modifier return from peered num increment'
        return False

    # check modifier sees increment
    if modifier.read_peered_num() != 23:
        print '\nErr: incorrect modifier return from peered num read'
        return False

    # check data reader sees increment
    if data_reader.read_peered_num() != 23:
        print '\nErr: incorrect data reader return from peered num read'
        return False

    # check modifier can increment
    if modifier.increment_peered_num() != 24:
        print '\nErr: incorrect second modifier return from peered num increment'
        return False

    if modifier.increment_peered_num() != 25:
        print '\nErr: incorrect second modifier return from peered num increment'
        return False

    

    
    # check work on peered map
    to_add_list = [
        ('r',{ 'a': True, 'b': False}),
        ('dl',{ 'a': False, 'b': False}),
        ('m',{ 'a': False, 'b': True}),
        ('dl',{ 'a': True, 'b': False})]
    first_time = True
    for index,inner_map_to_add in to_add_list:
        modifier.add_inner_map(index,inner_map_to_add)

        if data_reader.read_inner_map(index) != inner_map_to_add:
            print '\nErr: problem with updating peered nested map'
            return False

    return True


if __name__ == '__main__':
    run_test()
