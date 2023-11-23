from classes import Process

if __name__ == "__main__":

    port_number = input("Enter process port number \n")

    process = Process("0.0.0.0", int(port_number))
    process.start()

    # Give some time for nodes to start listening
    import time
    time.sleep(2)

    process.connect_to_rendezvous("127.0.0.1", 8000)

    # TODO: Update while loop.
    max_val = 4
    
    while(True):
        if max_val == 0:
            break
    