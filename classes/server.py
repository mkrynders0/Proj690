import socket
import threading
import json 

class Peer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = []
        self.out = []

    def encode_data(self, data):
        return json.dumps(data).encode('utf-8')
    
    def decode_data(self, data):
        return json.loads(data.decode('utf-8'))
    
    def connect(self, peer_host, peer_port):
        connection = socket.create_connection((peer_host, peer_port))

        self.connections.append(connection)
        print(f"Connected to {peer_host}:{peer_port}")

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
            print(f'sendng data to {connection}')
            try:
                connection.sendall(self.encode_data(data))
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
                decoded_data = self.decode_data(data)
                print(f"Received data from {address}: {decoded_data}")
                
                message_type = decoded_data.keys()

                if 'new' in message_type:
                    # If there is a new client, tell all other clients about it.
                    port_number = decoded_data['new']
                    # data = {'new': port_number}

                    connection = socket.create_connection(('127.0.0.1', port_number))   
                    self.connections.append(connection)
                    self.out.append(connection)
                    # self.send_data(data)

                    ports = self.currently_connected_ports()
                    print(ports)
                    if len(ports) > 0:
                        data = {'ports': ports}
                        encoded_data = self.encode_data(data)
                        connection.sendall(encoded_data)
                        
            except socket.error:
                break

        print(f"Connection from {address} closed.")
        self.connections.remove(connection)
        self.out.remove(connection)
        connection.close()

    def currently_connected_ports(self):
        port_numbers = []
        for connection in self.out:
            port_numbers.append(connection.getpeername()[1])
        return port_numbers

    def start(self):

        #test = self.socket.getpeername()
        # print(f"Self: {test}")
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()

# Example usage:
if __name__ == "__main__":
    node1 = Peer("0.0.0.0", 8000)
    node1.start()

    # node2 = Peer("0.0.0.0", 8001)
    # node2.start()

    # Give some time for nodes to start listening
    import time
    time.sleep(2)
    
    max_val = 4
    
    while(True):
        if max_val == 0:
            break

    # node2.connect("127.0.0.1", 8000)
    # time.sleep(1)  # Allow connection to establish
    # node2.send_data("Hello from node2!")