from util import Queue
import threading
import waldoServiceActions
import logging
import util

class _EndpointServiceThread(threading.Thread):
    def __init__(self,endpoint):
        '''
        @param {_Endpoint object} endpoint
        '''
        self.endpoint = endpoint

        # each element is an _Action (@see
        # waldoServiceActions._Action).
        self.threadsafe_queue = Queue.Queue()        
        threading.Thread.__init__(self)
        self.daemon = True

        self.logging_info = {
            'mod': 'EndpointServiceThread',
            'endpoint_string': self.endpoint._endpoint_uuid_str
            }
        
    def run(self):
        '''
        Event loop.  Keep on reading off queue and servicing.
        '''
        while True:
            service_action = self.threadsafe_queue.get()
            if __debug__:
                util.get_logger().debug(
                    ('Servicing action.  Remaining queue size: %s' %
                     str(self.threadsafe_queue.qsize())),
                    extra= self.logging_info)
            service_action.service()

    def receive_request_backout(self,uuid,requesting_endpoint):
        '''
        @param {uuid} uuid --- The uuid of the _ActiveEvent that we
        want to backout.

        @param {either Endpoint object or
        util.PARTNER_ENDPOINT_SENTINEL} requesting_endpoint ---
        Endpoint object if was requested to backout by endpoint objects
        on this same host (from endpoint object calls).
        util.PARTNER_ENDPOINT_SENTINEL if was requested to backout
        by partner.
        
        Called by another endpoint on this endpoint (not called by
        external non-Waldo code).
        '''
        req_backout_action = waldoServiceActions._ReceiveRequestBackoutAction(
            self.endpoint,uuid,requesting_endpoint)
        self.threadsafe_queue.put(req_backout_action)
        

    def receive_partner_ready(self):
        partner_ready_action = waldoServiceActions._ReceivePartnerReadyAction(
            self.endpoint)
        self.threadsafe_queue.put(partner_ready_action)
        
    def receive_request_complete_commit(self,event_uuid,request_from_partner):
        '''
        Another endpoint (either on the same host as I am or my
        partner) asked me to complete the second phase of the commit
        for an event with uuid event_uuid.
        
        @param {uuid} event_uuid --- The uuid of the event we are
        trying to commit.

        @param {bool} request_from_partner --- True if the request to
        complete the commit came from my partner, false otherwise (the
        request came from an endpoint on the same host as I am)
        '''
        req_complete_commit_action = (
            waldoServiceActions._ReceiveRequestCompleteCommitAction(
                self.endpoint,event_uuid,request_from_partner))
        
        self.threadsafe_queue.put(req_complete_commit_action)

    def receive_removed_subscriber(
        self,event_uuid,removed_subscriber_event_uuid,
        host_uuid,resource_uuid):
        '''
        @see _receive_additional_subscriber
        '''
        rem_sub_act = waldoServiceActions._ReceiveSubscriberAction(
            self.endpoint,event_uuid,removed_subscriber_event_uuid,
            host_uuid,resource_uuid,True)

        self.threadsafe_queue.put(rem_sub_act)

    def receive_additional_subscriber(
        self,event_uuid,additional_subscriber_event_uuid,
        host_uuid,resource_uuid):
        '''
        @see _Endpoint._receive_additional_subscriber
        '''
        rcv_sub_act = waldoServiceActions._ReceiveSubscriberAction(
            self.endpoint,event_uuid,additional_subscriber_event_uuid,
            host_uuid,resource_uuid,False)

        self.threadsafe_queue.put(rcv_sub_act)

    def receive_first_phase_commit_message(
        self,event_uuid,msg_originator_endpoint_uuid,successful,
        children_event_endpoint_uuids=None):
        '''
        @param {uuid} event_uuid --- The uuid of the event associated
        with this message.  (Used to index into local endpoint's
        active event map.)

        @param {uuid} msg_originator_endpoint_uuid --- The endpoint
        that tried to perform the first phase of the commit.  (Other
        endpoints may have forwarded the result on to us.)

        @param {bool} successful --- True if the endpoint with uuid
        msg_originator_endpoint_uuid was able to hold locks for the
        first phase of the commit and there were no conflicts.  False
        if the event must be invalidated because another event
        committed a conflict.

        @param {None or list} children_event_endpoint_uuids --- None
        if successful is False.  Otherwise, a set of uuids.  The root
        endpoint should not transition from being in first phase of
        commit to completing commit until it has received a first
        phase successful message from endpoints with each of these
        uuids.
        '''
        first_phase_commit_act = waldoServiceActions._ReceiveFirstPhaseCommitMessage(
            self.endpoint,event_uuid,msg_originator_endpoint_uuid,successful,
            children_event_endpoint_uuids)
        
        self.threadsafe_queue.put(first_phase_commit_act)
        
    def receive_endpoint_call(
        self,endpoint_making_call,event_uuid,func_name,result_queue,*args):
        '''
        @param{_Endpoint object} endpoint_making_call --- The endpoint
        that made the endpoint call into this endpoint.

        @param {uuid} event_uuid --- 

        @param {string} func_name --- The name of the Public function
        to execute (in the Waldo source file).

        @param {Queue.Queue} result_queue --- When the function
        returns, wrap it in a
        waldoEndpointCallResult._EndpointCallResult object and put it
        into this threadsafe queue.  The endpoint that made the call
        is blocking waiting for the result of the call. 

        @param {*args} *args --- additional arguments that the
        function requires.

        Called by another endpoint on this endpoint (not called by
        external non-Waldo code).
        '''
        endpt_call_action = waldoServiceActions._ReceiveEndpointCallAction(
            self.endpoint,endpoint_making_call,event_uuid,func_name,
            result_queue,*args)
        self.threadsafe_queue.put(endpt_call_action)

        
    def receive_partner_request_complete_commit(self,msg):
        '''
        @param {_PartnerCommitRequestMessage} msg
        '''
        partner_request_complete_commit_action = (
            waldoServiceActions._ReceiveRequestCompleteCommitAction(
                self.endpoint,msg.event_uuid,True))
        self.threadsafe_queue.put(partner_request_complete_commit_action)

        
    def receive_partner_request_message_sequence_block(self,msg):
        '''
        @param {_PartnerRequestSequenceBlockMessage} msg --- Contains
        all the information for the request partner made.
        '''
        partner_request_sequence_block_action = (
            waldoServiceActions._ReceivePartnerMessageRequestSequenceBlockAction(
                self.endpoint,msg))
            
        self.threadsafe_queue.put(partner_request_sequence_block_action)

    def receive_partner_notify_of_peered_modified_msg(self,msg):
        '''
        @param {waldoMessages._PartnerNotifyOfPeeredModified} msg
        '''
        action = waldoServiceActions._ReceivePeeredModifiedMsg(
            self.endpoint,msg)
        self.threadsafe_queue.put(action)

    def receive_partner_notify_of_peered_modified_rsp_msg(self,msg):
        '''
        @param {waldoMessages._PartnerNotifyOfPeeredModifiedResponse} msg
        '''
        action = waldoServiceActions._ReceivePeeredModifiedResponseMsg(
            self.endpoint,msg)
        self.threadsafe_queue.put(action)        

    def receive_partner_request_commit(self,msg):
        '''
        @param {_PartnerCommitRequestMessage} msg
        '''
        partner_request_commit_action = (
            waldoServiceActions._ReceiveRequestCommitAction(
                self.endpoint,msg.event_uuid,True))
        self.threadsafe_queue.put(partner_request_commit_action)
        
    def receive_request_commit_from_endpoint(self,uuid,requesting_endpoint):
        '''
        @param {uuid} uuid --- The uuid of the _ActiveEvent that we
        want to commit.

        @param {Endpoint object} requesting_endpoint --- 
        Endpoint object if was requested to commit by endpoint objects
        on this same host (from endpoint object calls).
        
        Called by another endpoint on this endpoint (not called by
        external non-Waldo code).

        Forward the commit request to any other endpoints that were
        touched when the event was processed on this side.
        '''
        endpoint_request_commit_action = (
            waldoServiceActions._ReceiveRequestCommitAction(
                self.endpoint,uuid,False))
        self.threadsafe_queue.put(endpoint_request_commit_action)

