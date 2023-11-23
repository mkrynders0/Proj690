import socket
import threading
import json

class Peer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = []
        self.server_connection = None

    def encode_data(self, data):
        return json.dumps(data).encode('utf-8')
    
    def decode_data(self, data):
        return json.loads(data.decode('utf-8'))

    def connect_to_rendezvous(self, server_host, server_port):
        # Connect and set server socket
        connection = socket.create_connection((server_host, server_port))
        self.connections.append(connection)
        self.server_connection = connection
        
        # Send port number to socket to connect to other nodes.
        encoded_data = self.encode_data({'new': self.port})
        connection.sendall(encoded_data)

    
    def connect(self, peer_host, peer_port):
        connection = socket.create_connection((peer_host, peer_port))

        self.connections.append(connection)
        print(f"Connected to {peer_host}:{peer_port}")
        return connection

    def listen(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        print(f"Listening for connections on {self.host}:{self.port}")

        while True:
            connection, address = self.socket.accept()
            self.connections.append(connection)
            print(f"Accepted connection from {address}")
            threading.Thread(target=self.handle_client, args=(connection, address)).start()

    def send_data(self, data):
        for connection in self.connections:
            try:
                connection.sendall(data.encode())
            except socket.error as e:
                print(f"Failed to send data. Error: {e}")
                self.connections.remove(connection)

    def handle_client(self, connection, address):
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
                            connection = self.connect("127.0.0.1", port)
                            print(f'Connected to new port {port} (resp)')
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

        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()

# Example usage:
if __name__ == "__main__":
    #node1 = Peer("0.0.0.0", 8000)
    #node1.start()

    node2 = Peer("0.0.0.0", 8001)
    node2.start()

    # Give some time for nodes to start listening
    import time
    time.sleep(2)

    node2.connect_to_rendezvous("127.0.0.1", 8000)

    # node2.connect("127.0.0.1", 8000)
    time.sleep(1)  # Allow connection to establish
    data = {"new": node2.port}

    max_val = 4
    
    while(True):
        if max_val == 0:
            break


    # node2.send_data("Hello from node2!")
    # node2.send_data("Hello from node2!")