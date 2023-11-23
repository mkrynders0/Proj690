from classes import Server

if __name__ == "__main__":
    server = Server("0.0.0.0", 8000)
    server.start()

    # Give some time for nodes to start listening
    import time
    time.sleep(2)
    
    # TODO: Update while function
    max_val = 4
    
    while(True):
        if max_val == 0:
            break

    