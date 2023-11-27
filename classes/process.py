"""Process

This class represents a process that can connect to a peer network and run an 
implementation of the flooding regular consensus protocol algorithm.
"""

import socket
import threading
import json

class Process:
    def __init__(self, host, port):
        # Socket Connections #
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = []
        self.server_connection = None

        # Flooding Algorithm #
        self.proposal_set = []    # List of all proposed values.
        self.decided_rounds = []  # List of round IDs that have been decided.

        self.received_from = dict()       # Dict of process ports that have been received from per round.
        self.proposed_for_round = dict()  # Flag for if the process proposed per round.

        self.current_round_id = 0                # ID of the current round.      
        self.current_accepted_addresses = set()  # Set of currently conencted receiving addresses.
        self.initial_out_ports = set()           # List of initial connections' ports from the current round's start.
        self.round_crash = False                 # Flag for if there has been a crash in the current round. 
       
        
    # ****************** #
    # Socket Connections #
    
    def encode_data(self, data):
        """Encodes dictionary data.
        
        Keyword arguments:
        data -- dictionary to be encoded.
        Return: encoded version of dictionary data.
        """
        return json.dumps(data).encode('utf-8')
    
    def decode_data(self, data):
        """Decodes dictionary data.
        May get multiple messages in a data stream, so need to split individual
        dict objects to load individually.

        Keyword arguments:
        data -- encoded string of dict(s) to be decoded.
        Return: list of decoded version of dict data.
        """
        # Decode data.
        decoded_data = data.decode('utf-8')

        # Split string per dict object.
        data_message = decoded_data.split('}')
        data_message = [i+'}' for i in data_message]
        data_message.remove('}')

        return [json.loads(i) for i in data_message]

    def connect_to_rendezvous(self, server_host, server_port):
        """Create connection to server to access group of peers.
        
        Keyword arguments:
        server_host -- host address of server connection.
        server_port -- port number of server connection.
        Return: N/A
        """
        # Connect and set server socket
        connection = socket.create_connection((server_host, server_port))
        self.connections.append(connection)
        self.server_connection = connection
        
        # Send message to server to get group of peers.
        encoded_data = self.encode_data({'new': self.port})
        connection.sendall(encoded_data)

    
    def connect(self, peer_host, peer_port):
        """Connect to a peer socket.
        
        Keyword arguments:
        peer_host -- host address of the peer connection.
        peer_port -- port number of the peer connection.
        Return: socket of new connection.
        """
        # Create socket to connect to the peer.
        connection = socket.create_connection((peer_host, peer_port))
        self.connections.append(connection)

        print(f"Now sending data to {peer_host}:{peer_port}")
        return connection
    
    def crash_connection(self, connection, address=None):
        """Handle a connection crash
        
        Keyword arguments:
        connection -- peer connection that has crashed.
        address -- tuple of host address/port for the crashed peer.
        Return: N/A
        """ 
        # Remove from current connections and close the connection.
        self.connections.remove(connection)
        connection.close()
        

        # Check address for crashed receive connections.
        if address:
            print(f"Connection from {address} closed.")
            self.current_accepted_addresses.remove(address)

            # Set crash flag.
            self.round_crash = True

            # Check if process has now received all values from updated current connections.
            self.check_end_of_round()

    def listen(self):
        """Listen to a socket connection for incoming data.
        There is a thread running per connection which calls to handle data once received.
        
        Return: N/A
        """
        # Start listening on receiving port.
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        print(f"Listening for connections on {self.host}:{self.port}")

        while True:
            # Infinite loop to handle receiving data via a thread per connected peer.
            connection, address = self.socket.accept()
            self.connections.append(connection)
            print(f"Now receiving data from connection: {address}")
            self.current_accepted_addresses.add(address)
            threading.Thread(target=self.handle_client, args=(connection, address)).start()

    def send_to_all(self, data):
        """Send data to all connections
        
        Keyword arguments:
        data -- Encoded data to be sent
        Return: N/A
        """
        print(f"Sending {data} to all.")
        for connection in self.connections:
            try:
                connection.sendall(self.encode_data(data))
            except socket.error as e:
                self.crash_connection(connection)
                continue

    def send_to_connection(self, data, connection):
        """Send data to a send port.
        
        Keyword arguments:
        data -- dict data to be sent.
        connection -- socket to send the data on.
        Return: N/A
        """
        try:
            connection.sendall(self.encode_data(data))
        except socket.error as e:
            self.crash_connection(connection)

    def handle_client(self, connection, address):
        """Receive and handle incoming data from connected nodes.
        
        Expected message types:
            New:      A process requests be added to this process's connections.
            Ports:    This process has received a list of currently active
                      peer ports that it needs to exchange connections with.
            Proposal: Receive a proposal set from a peer process.
            Decision: Receive a decided value from a peer process.

        Keyword arguments:
        connection -- socket that is receiving data.
        address -- tuple host address/port that is receiving data.
        Return: N/A
        """
        while True:
            try:
                # Receive data on connection
                data = connection.recv(1024)
                if not data:
                    break
                
                data_messages = self.decode_data(data) 
                print(f"Received data from {address}: {data_messages}")

                for data_message in data_messages:     
                    message_type = data_message.keys()

                    if 'new' in message_type:
                        # Connect to new node.
                        new_port = data_message['new']

                        if new_port != self.port:
                            # Connect to new peer process.
                            self.connect("127.0.0.1", new_port)

                    elif 'ports' in message_type:
                        # Connect to all other peers in the network.
                        ports = data_message['ports']
                        for port in ports:
                            if port != self.port:
                                # Connect to the new peer and equest to be added to the peer's connections.
                                new_connection = self.connect("127.0.0.1", port)
                                self.send_to_connection({'new': self.port}, new_connection)
                        # Last server communication, remove server from current.
                        self.current_accepted_addresses.remove(address)
                        print('Sent connections to all received ports.')

                    elif 'proposal' in message_type:
                        round_id =  data_message['proposal'][0]
                        proposal_set = data_message['proposal'][1]
                        self.receive_proposal(address, round_id, proposal_set)

                    elif 'decision' in message_type:
                        round_id = data_message['decision'][0]
                        decided_value = data_message['decision'][1]
                        if round_id not in self.decided_rounds:
                            self.decide(force_decision=decided_value, round_id=round_id)

                            # Only end round if receiving a decision for the current round.
                            if round_id == self.current_round_id:
                                self.end_round()

            except socket.error:
                self.crash_connection(connection=connection, address=address)
                break

    def start(self):
        """Start thread to listen for incoming connections.
        
        Return: N/A
        """
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()

    # ****************** #
    # Flooding Algorithm #

    def propose(self, value):
        """ Propose a user input value. 
        Add value to proposal set and broadcast to all connected nodes.
        
        Keyword arguments:
        value -- user entered value
        Return: N/A
        """
        # Add value to proposal set. 
        self.consolidate_proposal_sets([value])
        self.proposed_for_round[self.current_round_id] = True

        # Broadcast proposal set to all peers.
        self.send_to_all({'proposal': (self.current_round_id, self.proposal_set)}) 
        
        # Check if this was the last value needed for the round.
        self.check_end_of_round()

    def decide(self, round_id, force_decision=None):
        """Decide on a value.
        At the end of a round, the process will decide and broadcast a value if no connections have died during the round.
        The decision is based on the smallest value in the proposal set.
        
        Return: N/A
        """
        print(f"Starting decisionfor round {round_id}...")
        # Don't need to decide if round was already decided on.
        if round_id in self.decided_rounds:
            print(f"Has already decided for round {round_id}.")
            return
        self.decided_rounds.append(round_id)

        if force_decision:
            # Force decision if a decision has been received from another process for this round.
            self.consolidate_proposal_sets([force_decision])
            val = force_decision
        else:
            # Set decided val to largest val in list.
            val = self.proposal_set[-1]
      
        
        print(f'** Process has decided on value {val} for round {round_id}.**\n')

        # Broadcast decision to all peers.
        self.send_to_all({'decision': (self.current_round_id, val)})

    def check_end_of_round(self):
        """Determine if the process has reached the end of the currenet round.
        A process has reached the end if it has received proposals from all currently connected nodes for the round.
        
        Return: N/A
        """
        # Check if the process has received all possible values from the current connections.
        print(f"Checking end of round {self.current_round_id}...")
        received_all_possible = False
        
        if self.current_round_id in self.received_from.keys():

            # Get list of addresses that the process has received proposals from.
            received_from_addresses = self.received_from[self.current_round_id]

            # Determine if the process has proposed a value for the round.
            has_proposed = self.proposed_for_round[self.current_round_id] if self.current_round_id in self.proposed_for_round.keys() else False

            # Check if process has received all possible proposals from self and  peer processes. Add one for server connection.
            received_all_possible = self.current_accepted_addresses.issubset(received_from_addresses) and has_proposed

        if received_all_possible:
            # End the round.
            if not self.round_crash:
                # Only decide on a value if there have been no crashes in the current round.
                self.decide(round_id=self.current_round_id)
                
            self.end_round()
        else:
            print("Round should not end.")

    def end_round(self):
        """End the current round and reset for the next round.
        
        Return: N/A
        """
        print(f"Ending round {self.current_round_id}...\n")
        # Increment the round ID and reset the round's initial connections.
        self.current_round_id += 1 
        self.initial_accepted_addresses = self.current_accepted_addresses

        # Needs chance to decide again this round if there were crashes in previous round.
        if self.round_crash:
            self.proposed_for_round[self.current_round_id] = True
            # Broadcast proposal set to all peers for past round in case of crash.
            self.send_to_all({'proposal': (self.current_round_id, self.proposal_set)}) 
        else:
            self.proposed_for_round[self.current_round_id] = False

        self.round_crash = False
        print(f"Starting new round {self.current_round_id}\n****************")

    def consolidate_proposal_sets(self, proposal_set):
        """Add a proposal to this process's proposal set.
        
        Keyword arguments:
        proposal_set -- list of proposal(s) that need to be added to the process proposal set.
        Return: N/A
        """
        self.proposal_set = sorted(list(set(self.proposal_set) | set(proposal_set)))
        print(f"Updated Set: {self.proposal_set}")

    def receive_proposal(self, address, round_id, proposal_set):
        """ Receive a proposal from a connected node.
        Record that a value has been received from a node during a specified round.
        
        Keyword arguments:
        address --  tuple host address/port for recieving proposal data.
        round_id -- int ID of the round in which the value was proposed.
        proposed_set -- list of set including updated proposed value.
        Return: N/A
        """
        if round_id in self.received_from.keys():
            # If round_id has already been received, add address to that round.
            self.received_from[round_id].add(address)
        else:
            # If round has not yet been received from, initialize round ID as key and add address.
            self.received_from[round_id] = {address}

        # Update self proposal set and check if it was the last possible recieved to conclude the round.
        self.consolidate_proposal_sets(proposal_set)
        self.check_end_of_round()
        