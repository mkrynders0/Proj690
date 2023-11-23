import socket
import threading
import json 

class Server:
    def __init__(self, host, port):
        self.host = host  # Host address.
        self.port = port  # Port number for connection.
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP Socket.
        self.connections = []  # List of sockets for In and Out connections.
        self.out = []  # List of only Out connections.

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
    
    def connect(self, peer_host, peer_port):
        """Connect to a peer socket.
        
        Keyword arguments:
        peer_host -- host address of the peer connection
        peer_port -- port number of the peer connection
        Return: N/A
        """
        # Create socket to connect to the peer.
        connection = socket.create_connection((peer_host, peer_port))
        self.connections.append(connection)

        print(f"Connected to {peer_host}:{peer_port}")

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
            threading.Thread(target=self.receive_data, args=(connection, address)).start()

    def send_data(self, data):
        """Send data to all connections
        
        Keyword arguments:
        data -- Encoded data to be sent
        Return: N/A
        """
        for connection in self.connections:
            print(f'sendng data to {connection}')
            try:
                connection.sendall(self.encode_data(data))
            except socket.error as e:
                print(f"Failed to send data. Error: {e}")
                self.connections.remove(connection)

    def receive_data(self, connection, address):
        """Receive and handle incoming data from connected nodes.
        
        Expected message types:
            New: A process wants to be added to the group of peers. 
                 Need to let the new process know about all other connected peers.

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
                decoded_data = self.decode_data(data)
                print(f"Received data from {address}: {decoded_data}")
                
                # Get which type of message was sent.
                message_type = decoded_data.keys()

                if 'new' in message_type:
                    # Get the port number of the new connection.
                    port_number = decoded_data['new']

                    # Add that connection to the Out connections.
                    connection = socket.create_connection(('127.0.0.1', port_number))   
                    self.connections.append(connection)
                    self.out.append(connection)

                    # Get all currently connected Out ports and send to the new connection.
                    ports = self.currently_connected_ports()
                    print(ports)
                    if len(ports) > 0:
                        data = {'ports': ports}
                        encoded_data = self.encode_data(data)
                        connection.sendall(encoded_data)
                        
            except socket.error:
                break

        # If there was an error (e.g., a crash), need to remove the process from the group.
        print(f"Connection from {address} closed.")
        self.connections.remove(connection)
        self.out.remove(connection)
        connection.close()

    def currently_connected_ports(self):
        """Get port numbers of all current Out connections.
        
        Return: list of int port numbers
        """
        port_numbers = []
        for connection in self.out:
            port_numbers.append(connection.getpeername()[1])
        return port_numbers

    def start(self):
        """Start thread to listen for incoming connections.
        
        Return: N/A
        """
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()
