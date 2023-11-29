import socket
import threading
import json

class Process:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = []
        self.server_connection = None
        self.port_address_map = dict()

        # Flooding Algorithm
        self.proposal_set = []           # List of all proposed values.
        self.decided_rounds = []         # List of round IDs that have been decided.
        self.current_out_ports = set()   # List of out ports currently connected.
        self.initial_out_ports = set()   # List of initial connections' ports from the current round's start.
        self.received_from = dict()      # Dict of process ports that have been received from per round.
        self.current_round_id = 0        # ID of the current round.
        self.proposed_this_round = False # T/F has the process proposed for this round.
        self.round_crash = False

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
        
        Keyword arguments:
        data -- dictionary to be decoded.
        Return: decoded version of dictionary data.
        """
        return json.loads(data.decode('utf-8'))

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

    
    def connect(self, address, peer_host, peer_port):
        """Connect to a peer socket.
        
        Keyword arguments:
        peer_host -- host address of the peer connection.
        peer_port -- port number of the peer connection.
        Return: socket of new connection.
        """
        # Create socket to connect to the peer.
        connection = socket.create_connection((peer_host, peer_port))
        self.connections.append(connection)
        self.current_out_ports.add(peer_port)
        self.port_address_map[address[1]] = peer_port

        print(f"Connected to {peer_host}:{peer_port} on {connection.getpeername()[1]}")
        return connection
    
    def crash_connection(self, connection, address=None):
        """Handle a connection crash
        
        Keyword arguments:
        connection -- peer connection that has crashed.
        address -- host address of the crashed peer.
        Return: N/A
        """
        print(f"Connection from {address} closed.")
        # Set crash flag
        self.round_crash = True

        # Remove from current connections and close the connection.
        self.connections.remove(connection)
        self.current_out_ports.remove(self.port_address_map[address[1]])
        connection.close()

        # Check if process has now received all values from updated current connections.
        # TODO: Need to check for all past rounds...?
        self.check_end_of_round()

    def listen(self):
        """Listen to a socket connection for incoming data.
        There is a thread running per connection which calls to handle data once received.
        
        Return: N/A
        """
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        print(f"Listening for connections on {self.host}:{self.port}")

        while True:
            connection, address = self.socket.accept()
            self.connections.append(connection)
            print(f"Accepted connection from {address}")
            threading.Thread(target=self.handle_client, args=(connection, address)).start()

    def send_data(self, data):
        """Send data to all connections
        
        Keyword arguments:
        data -- Encoded data to be sent
        Return: N/A
        """
        for connection in self.connections:
            try:
                connection.sendall(self.encode_data(data))
            except socket.error as e:
                print(e)
                # TODO: This might actually be the port number already
                self.crash_connection(connection.getpeername()[1])

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
        address -- address of the sending socket.
        Return: N/A
        """
        while True:
            try:
                # Receive data on connection
                data = connection.recv(1024)
                if not data:
                    break
                data_message = self.decode_data(data) 
                print(f"Received data from {address}: {data_message}")
                      
                message_type = data_message.keys()

                if 'new' in message_type:
                    # Connect to new node.
                    new_port = data_message['new']

                    if new_port != self.port:
                        # Connect to new node
                        self.connect(address, "127.0.0.1", new_port)
                        print(f'Connected to new port {new_port}')

                elif 'ports' in message_type:
                    # Connect to all other peers in the network.
                    ports = data_message['ports']
                    for port in ports:
                        if port != self.port:
                            # Connect to the new peer.
                            new_connection = self.connect(address, "127.0.0.1", port)

                            # Request to be added to the peer's connections.
                            new_connection.sendall(self.encode_data({'new': self.port}))

                elif 'proposal' in message_type:
                    round_id =  data_message['proposal'][0]
                    proposal_set = data_message['proposal'][1]
                    self.receive_proposal(self.port_address_map[address[1]], round_id, proposal_set)

                elif 'decision' in message_type:
                    round_id = data_message['decision'][0]
                    decided_value = data_message['decision'][1]
                    self.decide(force_decision=decided_value, round_id=round_id)

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
        self.proposed_this_round = True

        # Broadcast proposal set to all peers.
        self.send_data({'proposal': (self.current_round_id, self.proposal_set)}) 
        
        # Check if this was the last value needed for the round.
        self.check_end_of_round()

    def decide(self, round_id, force_decision=None):
        """Decide on a value.
        At the end of a round, the process will decide and broadcast a value if no connections have died during the round.
        The decision is based on the smallest value in the proposal set.
        
        Return: N/A
        """
        # Don't need to decide if round was already decided on.
        if round_id in self.decided_rounds:
            return
        
        if force_decision:
            # Force decision if a decision has been received from another process for this round.
            self.consolidate_proposal_sets([force_decision])
            val = force_decision
        else:
            # Set decided val to largest val in list.
            val = self.proposal_set[-1]
      
        self.decided_rounds.append(round_id)
        print(f'Process has decided on value {val} for round {round_id}.')

        # Broadcast decision to all peers.
        self.send_data({'decision': (self.current_round_id, val)}) 

    def check_end_of_round(self):
        """Determine if the process has reached the end of the currenet round.
        A process has reached the end if it has received proposals from all currently connected nodes for the round.
        
        Return: N/A
        """
        # Check if the process has received all possible values from the current connections.
        print("Checking end of round")
        received_all_possible = False
        if self.current_round_id in self.received_from.keys():
            print(f"Received from this round {self.received_from[self.current_round_id]}?\n")
            print(f"Current out ports {self.current_out_ports}")

            received_from_ports = self.received_from[self.current_round_id]

            received_all_possible = len(received_from_ports) == len(self.current_out_ports) and \
                set(received_from_ports).issubset(set(self.current_out_ports)) and \
                self.proposed_this_round

        if received_all_possible:
            # End the round.
            if not self.round_crash:
                # Only decide on a value if there have been no crashes in the current round.
                self.decide(round_id=self.current_round_id)
            self.end_round()

    def end_round(self):
        """End the current round and reset for the next round.
        
        Return: N/A
        """
        # Increment the round ID and reset the round's initial connections.
        self.current_round_id += 1 
        self.initial_out_ports = self.current_out_ports

        # Reset round flags
        self.proposed_this_round = self.round_crash = False

        # Broadcast proposal set to all peers.
        self.send_data({'propose': self.proposal_set}) 

    def consolidate_proposal_sets(self, proposal_set):
        """Add a proposal to this process's proposal set.
        
        Keyword arguments:
        proposal_set -- list of proposal(s) that need to be added to the process proposal set.
        Return: N/A
        """
        self.proposal_set = sorted(list(set(self.proposal_set) | set(proposal_set)))
        print(f"consolidated set: {self.proposal_set}")

    def receive_proposal(self, port_number, round_id, proposal_set):
        """ Receive a proposal from a connected node.
        Record that a value has been received from a node during a specified round.
        
        Keyword arguments:
        port -- int port number of the node that sent the proposal.
        round_id -- int ID of the round in which the value was proposed.
        proposed_value -- str value to be appended to the proposal set.
        Return: N/A
        """
        print(f"Receive proposal from {port_number}")
        # Add port to received from for the specified round.
        if round_id in self.received_from.keys():
            # If round_id has already been received, add port to that round.
            self.received_from[round_id].append(port_number)
        else:
            # If round has not yet been received from, initialize round ID as key and add port.
            self.received_from[round_id] = [port_number]

        # Add value to set and check if it was the last possible value to conclude the round.
        self.consolidate_proposal_sets(proposal_set)
        self.check_end_of_round()
        