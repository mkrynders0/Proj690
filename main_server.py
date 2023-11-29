"""Main program to run a rendezvous server.

Runs infinitely to listen for processes wanting to join the peer network.
"""

from classes import Server

if __name__ == "__main__":

    # Start server.
    server = Server("0.0.0.0", 8000)
    server.start()

    # Give some time for server to start listening.
    import time
    time.sleep(2)
    
    while(True):
        pass
