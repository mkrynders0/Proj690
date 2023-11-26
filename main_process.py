from classes import Process

if __name__ == "__main__":

    port_number = input("Enter process port number: \n")

    process = Process("0.0.0.0", int(port_number))
    process.start()

    # Give some time for nodes to start listening
    import time
    time.sleep(2)

    process.connect_to_rendezvous("127.0.0.1", 8000)

    # TODO: Update while loop.
    max_val = 4
    
    while(True):
        current_round_id = process.current_round_id
        if current_round_id not in process.proposed_for_round.keys() or not process.proposed_for_round[current_round_id]:
            proposed_value = input(f"*** Waiting for round {current_round_id} proposal...\n")
            process.propose(proposed_value)
        while (True):
            if process.current_round_id != current_round_id:
                break
    