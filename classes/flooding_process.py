"""
Each process maintains set of SEEN proposed values. 
Each round:
    Proposed set starts with its own proposed value
    Process broadcasts its set in Proposal message.
    When a process receives a proposal, it merges the sets.
    End of round is reached when it receives all possible proposals. 
    At the end, specific value is decided on IF no crash detections. If there is a detection, it just moves to the next round.
    If within a round, a decide is received from a previous or current round, it accepts that value.
    Moving to new round, set is extended rather than rewritten? 
    

Every proposal message is tagged with a round ID.
All received proposals must match the round ID.

"""

class FloodingProcess():
    def __init__(self, host_address, process_id):
        self.proposal_set = []         # List of all proposed values.
        self.received_from = dict()    # Process list from which proposals have been received per round.
        self.current_round_id = 0      # ID of the current round.
        self.initial_connections = []  # List of connected processes from the beginning per round.
        self.crashed_connections = []  # List of processes that crashed per round.
        self.id = process_id
        self.current_connections = []
        self.decided_rounds = []
        self.proposed_this_round = False

        super().__init__(host_address, port_number=process_id)

    def propose(self, value):
        """ Propose a user input value. 
        Add value to proposal set and broadcast to all connected nodes.
        
        Keyword arguments:
        value -- user entered value
        Return: N/A
        """
        # Add value to proposal set. 
        self.proposal_set.append(value)
        self.proposal_set = sorted(self.proposal_set)
        self.proposed_this_round = True

        # Broadcast set to peer nodes.
        self.broadcast_proposal_set()
        
        # Check if this was the last value needed for the round.
        self.check_end_of_round()

    def broadcast_proposal_set(self):
        current_connections = set(self.initial_connections) - set(self.crashed_connections)
        if current_connections:
            for process in current_connections:
                process.receive_proposal_set(process=self, round_id=self.current_round_id, proposal_set=self.proposal_set)

    def receive_proposal_set(self, process, round_id, proposal_set):
        """ Receive a proposal from a connected node.
        Record that a value has been received from a node during a specified round.
        
        Keyword arguments:
        process_id -- int ID of the node that has sent the proposal.
        round_id -- int ID of the round in which the value was proposed.
        proposed_value -- str value to be appended to the proposal set.
        Return: N/A
        """
        if round_id in self.received_from.keys():
            # If round_id has already been received, add process ID to that round.
            self.received_from[round_id].append(process)
        else:
            # If round has not yet been received from, initialize round ID as key and add process ID.
            self.received_from[round_id] = [process]

        # Add value to set and check if it was the last possible value to conclude the round.
        self.proposal_set = sorted(list(set(self.proposal_set) | set(proposal_set)))
        self.check_end_of_round()

    def receive_decision(self, round_id, decided_value):
        if round_id not in self.decided_rounds:
            self.decide(force_decision=decided_value, round_id=round_id)

    def receive_crash(self, process_id):
        """Receive a crash from a connected node.
        Record that a connected node has been killed.
        
        Keyword arguments:
        process_id -- int ID of the process that has crashed.
        Return: N/A
        """
        self.crashed_connections.append(process_id)
        self.check_end_of_round()


    def check_end_of_round(self):
        """Determine if the process has reached the end of the currenet round.
        A process has reached the end if it has received proposals from all currently connected nodes for the round.
        
        Keyword arguments:
        N/A
        Return: N/A
        """
        current_connections = set(self.initial_connections) - set(self.crashed_connections)
        received_all_possible = current_connections == set(self.received_from[self.current_round_id]) and self.proposed_this_round \
            if self.current_round_id in self.received_from.keys() else False   

        if received_all_possible:
            if not self.crashed_connections:
                # The process can only make a decision if no processes crashed during the round. 
                self.decide(round_id=self.current_round_id)
                
            self.end_round()

    def decide(self, round_id, force_decision=None):
        """Decide on a value.
        At the end of a round, the process will decide and broadcast a value if no connections have died during the round.
        The decision is based on the smallest value in the proposal set.
        
        Keyword arguments:
        N/A
        Return: N/A
        """
        if force_decision:
            self.proposal_set.append(force_decision)
            self.proposal_set = list(set(self.proposal_set))
            self.proposal_set = sorted(self.proposal_set)
            val = force_decision
        else:
            val = self.proposal_set[-1]

        if round_id in self.decided_rounds:
            return
        
        self.decided_rounds.append(round_id)
        print(f'Process {self.id} has decided on value {val} for round {round_id}.')

        # TODO: Broadcast decision to all connections
        current_connections = set(self.initial_connections) - set(self.crashed_connections)
        if current_connections:
            for process in current_connections:
                process.receive_decision(round_id=self.current_round_id, decided_value=val)

    def end_round(self):
        self.current_round_id += 1 
        self.crashed_connections = []
        self.initial_connections = self.get_current_connections()
        self.proposed_this_round = False

        # TODO: broadcast set for some reason.

    def get_current_connections(self):
        # TODO: Update to get current
        return self.current_connections
