#!/usr/bin/env python

import os
import sys

sys.path.append(
    os.path.join('..','..','lib'))

import wVariables

import wVariables
import commitManager
import invalidationListener
import time

'''
This test runs through and just determines how fast we can create a
single event, which increments a variable NUM_ITERATIONS times.  (This
is in contrast to increment_single_number_separate_events.py, which
checks how fast we can create separate events for each time we
increment the variable.  The two together gives us a sense of how much
overhead there is in creating an event.)
'''


class BasicTestInvalidationListener(invalidationListener._InvalidationListener):
    def notify_invalidated(self,wld_obj):
        pass

NUM_ITERATIONS = 100000
    
def run_test():
    commit_manager = commitManager._CommitManager()
    number = wVariables.WaldoNumVariable('some num',22)

    start = time.time()
    evt1 = BasicTestInvalidationListener(commit_manager)        
    for i in range(0,NUM_ITERATIONS):
        val = number.get_val(evt1)
        number.write_val(evt1,val+1)        
    evt1.hold_can_commit()
    evt1.complete_commit()

    elapsed = time.time() - start
    print '\n\n'
    print elapsed
    print '\n\n'        
    

if __name__ == '__main__':
    run_test()