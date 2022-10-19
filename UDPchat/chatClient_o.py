from socket import *
import time
import threading


class Client:

    def __init__(self, user_name, server_ip, server_port, client_port):
        self.user_name = user_name
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_port = client_port
        self.ack_rcv_c = False
        self.ack_rcv_s = False
        self.online = True

    def process_incoming(self, to_split, header, client_reg_table, l_sock, server_address):
        from_name = to_split[1]

        if header == '1':
            client_table = ""
            for i in range(2, len(to_split)):
                client_table = client_table + to_split[i] + "\n"
            with open(client_reg_table, "w") as reg_table:
                reg_table.write(client_table)

        elif header == '2':
            msg = to_split[2]
            print("\n>>> message received from " + from_name + ": " + msg)
            # send ack
            with open(client_reg_table, "r") as reg_table:
                Lines = reg_table.readlines()
                port_num = 0
                # search the table for client IP and listening port
                for line in Lines:
                    if from_name in line:
                        temp = line.split()
                        port_num = int(temp[3])
                        break
                ack = "ack_c\n" + from_name + "\nempty"  # from_name is not actually right here should be rcv name
                l_sock.sendto(ack.encode(), (server_address[0], port_num))

        elif header == '3':
            o_msg = ""
            for i in range(2, len(to_split)):
                o_msg = o_msg + to_split[i] + "\n"
            print(o_msg)

        elif header == '4':
            msg = to_split[2]
            print("\n>>> Channel_Message " + from_name + ": " + msg)

        elif header == '5':
            error_msg = to_split[2]
            print("\n>>> " + error_msg)

        elif header == 'ack_c':
            self.ack_rcv_c = True

        elif header == 'ack_s':
            self.ack_rcv_s = True

        elif header == 'ping':
            # only respond to pings if client is "online", meaning has deregistered.
            if self.online:
                to_send = "ack\n" + self.user_name + '\nempty'
                l_sock.sendto(to_send.encode(), server_address)

        else:
            print("\n>>> Received invalid header")

        print("\n>>> ", end="")

    def rcv(self, client_port, client_reg_table):
        l_sock = socket(AF_INET, SOCK_DGRAM)
        l_sock.bind(('', int(client_port)))

        while True:
            buf, server_address = l_sock.recvfrom(4096)
            buf = buf.decode()
            to_split = buf.splitlines()
            header = to_split[0]

            incoming = threading.Thread(target=self.process_incoming, args=(to_split, header, client_reg_table,
                                                                       l_sock, server_address,))
            incoming.start()

    def run_client(self):

        client_reg_table = self.user_name + "_reg_table.txt"
        # this socket is only used for the initial registration. Afterward all communication is handled
        # by a different listening socket and multithreading.
        clientSocket = socket(AF_INET, SOCK_DGRAM)

        to_send = "R\n" + self.user_name + "\n" + self.client_port
        try:
            clientSocket.sendto(to_send.encode(), (self.server_ip, self.server_port))
        except:
            print("\n>>> Invalid IP address")
            exit(3)

        welcome, serverAddress = clientSocket.recvfrom(4096)
        print(welcome.decode())

        header, server_address = clientSocket.recvfrom(4096)
        header = header.decode()

        if header == '0':
            tableStatus, serverAddress = clientSocket.recvfrom(4096)
            print(tableStatus.decode())
            client_table, serverAddress = clientSocket.recvfrom(4096)
            client_table = client_table.decode()
            with open(client_reg_table, "w") as reg_table:
                reg_table.write(client_table)
        elif header == '5':
            exit(3)

        listen = threading.Thread(target=self.rcv, args=(self.client_port, client_reg_table,))
        listen.start()

        while True:
            print("\n>>> ", end="")
            temp = input()
            input_list = temp.split()
            try:
                input_flag = input_list[0]
            except:
                print("\n>>> Invalid input")
                continue

            if input_flag == "dereg":
                try:
                    name_check = input_list[1]
                except:
                    print("\n>>> No recipient entered")
                    continue

                if self.user_name == input_list[1]:
                    to_send = "D\n" + self.user_name + "\n" + "empty"
                    for i in range(5):
                        clientSocket.sendto(to_send.encode(), (self.server_ip, self.server_port))
                        time.sleep(.5)
                        if self.ack_rcv_s:
                            print("\n>>> You are Offline. Bye")
                            self.online = False
                            break

                    if not self.ack_rcv_s:
                        print("\n>>> Server not responding")
                        print("\n>>> Exiting")
                        exit(2)
                else:
                    print("\n>>> Cannot deregister other users")

                self.ack_rcv_c = False
                self.ack_rcv_s = False

            elif input_flag == "send":
                # error check the inputs
                try:
                    target_name = input_list[1]
                except:
                    print("\n>>> No recipient entered")
                    continue

                try:
                    check_msg = input_list[2]
                except:
                    print("\n>>> No message entered")
                    continue

                msg = ""
                for i in range(2, len(input_list)):
                    msg = msg + input_list[i] + " "

                # read the table into a dictionary and use that to send
                reg_dict = {}
                with open(client_reg_table, "r") as table:
                    for line in table:
                        entry = line.split(": ")
                        reg_dict[entry[0]] = entry[1]
                    try:
                        target = reg_dict[target_name].split()
                    except:
                        print("\n>>> Invalid recipient name")
                        continue
                    if target[3] == "online":
                        to_send = "2\n" + self.user_name + "\n" + msg
                        clientSocket.sendto(to_send.encode(), (target[0], int(target[2])))

                        # wait for ack from client
                        time.sleep(.5)
                        if self.ack_rcv_c:
                            print("\n>>> Message received by " + target_name)
                        else:
                            to_send = "O\n" + self.user_name + "\n" + target_name + "\n" + msg
                            clientSocket.sendto(to_send.encode(), (self.server_ip, self.server_port))
                            print("\n>>> No ACK from " + target_name + ", message sent to server")

                            # wait for ack from server
                            time.sleep(.5)
                            if self.ack_rcv_s:
                                print("\n>>> Messages received by the server and saved")
                            else:
                                print("\n>>> Problem with server, messages not saved")
                    else:
                        to_send = "O\n" + self.user_name + "\n" + target_name + "\n" + msg
                        clientSocket.sendto(to_send.encode(), (self.server_ip, self.server_port))
                        time.sleep(.5)
                        if self.ack_rcv_s:
                            print("\n>>> Messages received by the server and saved")
                        else:
                            print("\n>>> Problem with server, messages not saved")

                self.ack_rcv_c = False
                self.ack_rcv_s = False

            elif input_flag == "reg":
                try:
                    name_check = input_list[1]
                except:
                    print("\n>>> No recipient entered")
                    continue

                if self.user_name == input_list[1]:
                    to_send = "B\n" + self.user_name + "\n" + "empty"
                    clientSocket.sendto(to_send.encode(), (self.server_ip, self.server_port))
                    self.online = True
                else:
                    print("\n>>> Cannot register other users")

            elif input_flag == "send_all":
                try:
                    check_msg = input_list[1]
                except:
                    print("\n>>> No message entered")
                    continue

                msg = ""
                for i in range(1, len(input_list)):
                    msg = msg + input_list[i] + " "
                to_send = "G\n" + self.user_name + "\n" + msg
                for i in range(5):
                    clientSocket.sendto(to_send.encode(), (self.server_ip, self.server_port))
                    time.sleep(.5)
                    if self.ack_rcv_s:
                        print("\n>>> Message received by Server")
                        break
                if not self.ack_rcv_s:
                    print("\n>>> Server not responding")

                self.ack_rcv_c = False
                self.ack_rcv_s = False

            else:
                print("\n>>> invalid input, try again")
