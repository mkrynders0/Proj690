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

    def encode_data(self, data):
        """Encodes dictionary data 
        
        Keyword arguments:
        data -- dictionary to be encoded
        Return: encoded version of dictionary data
        """
        return json.dumps(data).encode('utf-8')
    
    def decode_data(self, data):
        """Decodes dictionary data 
        
        Keyword arguments:
        data -- dictionary to be decoded
        Return: decoded version of dictionary data
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

        print(f"Connected to {peer_host}:{peer_port}")
        return connection

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
                connection.sendall(data.encode())
            except socket.error as e:
                print(f"Failed to send data. Error: {e}")
                self.connections.remove(connection)

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
                        connection = self.connect("127.0.0.1", new_port)
                        print(f'Connected to new port {new_port}')
                elif 'ports' in message_type:
                    # Connect to all other nodes in the network.
                    ports = data_message['ports']
                    for port in ports:
                        if port != self.port:
                            # Connect to the new connection.
                            connection = self.connect("127.0.0.1", port)
                            print(f'Connected to new port {port} (resp)')

                            # Request to be added to the node's connections.
                            connection.sendall(self.encode_data({'new': self.port}))
                elif 'proposal' in message_type:
                    pass
                elif 'decision' in message_type:
                    pass

            except socket.error:
                break

        print(f"Connection from {address} closed.")
        self.connections.remove(connection)
        connection.close()

    def start(self):
        """Start thread to listen for incoming connections.
        
        Return: N/A
        """
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()
        