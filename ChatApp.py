import sys
from UDPchat.chatServer_o import *
from UDPchat.chatClient_o import *


if __name__ == '__main__':
    try:
        mode = sys.argv[1]

        if mode == '-s':
            # in server mode
            server_port = int(sys.argv[2])
            if server_port < 1024 or server_port > 65535:
                print("Invalid port number")
                exit(3)
            server = Server(server_port)
            server.run_server()
        elif mode == '-c':
            # in client mode
            user_name = sys.argv[2]
            server_ip = sys.argv[3]
            server_port = int(sys.argv[4])
            client_port = sys.argv[5]

            if server_port < 1024 or server_port > 65535:
                print("Invalid port number")
                exit(3)
            if int(client_port) < 1024 or int(client_port) > 65535:
                print("Invalid port number")
                exit(3)
            client = Client(user_name, server_ip, server_port, client_port)
            client.run_client()
        else:
            print("Entered invalid mode flag")
    except:
        print("Invalid commandline arguments")
        exit(3)
