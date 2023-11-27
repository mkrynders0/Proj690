"""" Main program to run a single process.

Starts the process, connects to peers, and infinitely loops to carry out 
the flooding protocol with its peers.
"""

from classes import Process


if __name__ == "__main__":

    # Get port number for process.
    port_number = input("Enter process port number: \n")

    # Start process thread.
    process = Process("0.0.0.0", int(port_number))
    process.start()

    # Give some time for process to start listening.
    import time
    time.sleep(2)

    # Conenct to psuedo rendezvous server.
    process.connect_to_rendezvous("127.0.0.1", 8000)
    
    # Loop for each proposal round input.
    while(True):
        current_round_id = process.current_round_id
        # Only ask for proposal if round has not already been proposed for (e.g., in a case of a crash).
        if current_round_id not in process.proposed_for_round.keys() or not process.proposed_for_round[current_round_id]:
            proposed_value = input(f"** Waiting for round {current_round_id} proposal... **\n")
            process.propose(proposed_value)
        while (True):
            # Move to the next proposal input once a new round has been incremented.
            if process.current_round_id != current_round_id:
                break
    