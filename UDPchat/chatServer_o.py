#chat_server
from socket import *
import time
import threading


class Server:

    def __init__(self, port):
        self.server_port = port
        self.ack_rcv = {}

    def ping(self, serverSocket, regDict, target_name):
        # ping client for ack
        to_send = "ping\nserver\nempty"
        temp = regDict[target_name].split()
        new_address = (temp[0], int(temp[2]))
        serverSocket.sendto(to_send.encode(), new_address)
        self.ack_rcv[target_name] = False

    def send_ack(self, serverSocket, regDict, user_name):
        ack = "ack_s\nserver\nempty"
        temp = regDict[user_name].split()
        new_address = (temp[0], int(temp[2]))
        serverSocket.sendto(ack.encode(), new_address)

    def change_status(self, target_name, regDict, status):
        address_string = regDict[target_name]
        client_status = status
        temp = address_string.rsplit(' ', 1)[0]
        # convert client tuple to string and store in dictionary with name as key
        client_entry = temp + " " + client_status
        regDict[target_name] = client_entry

    def broadcast_table(self, serverSocket, regDict, user_name):
        table_entry = ""
        for name, entry in regDict.items():
            table_entry = table_entry + name + ": " + entry + "\n"

        for name, entry in regDict.items():
            if "online" in entry and name != user_name:
                to_send = "1\n" + "server\n" + table_entry
                temp = entry.split()
                new_address = (temp[0], int(temp[2]))
                serverSocket.sendto(to_send.encode(), new_address)

    def handle_expect(self, serverSocket, client_address, to_split, regDict):
        expect = to_split[0]
        user_name = to_split[1]
        msg = to_split[2]

        if expect == "R":
            # Register new client
            client_listen_port = msg
            address_string = ""
            client_status = "online"

            # convert client tuple to string and store in dictionary with name as key
            for element in client_address:
                address_string = address_string + str(element) + " "
            client_entry = address_string + client_listen_port + " " + client_status

            if user_name in regDict:
                welcome = "\n>>> Username already exists, please register with a different name"
                serverSocket.sendto(welcome.encode(), client_address)
                header = '5'
                serverSocket.sendto(header.encode(), client_address)

            else:
                regDict[user_name] = client_entry

                welcome = "\n>>> Welcome, you are now registered"
                serverSocket.sendto(welcome.encode(), client_address)

                # send header flag 0 indicate initial table will follow.
                header = '0'
                serverSocket.sendto(header.encode(), client_address)
                tableStatus = "\n>>> Client table updated"
                serverSocket.sendto(tableStatus.encode(), client_address)

                table_entry = ""
                for name, entry in regDict.items():
                    table_entry = table_entry + name + ": " + entry + "\n"
                serverSocket.sendto(table_entry.encode(), client_address)

                self.broadcast_table(serverSocket, regDict, user_name)

        elif expect == "D":
            self.change_status(user_name, regDict, 'offline')

            # send the ack
            self.send_ack(serverSocket, regDict, user_name)
            self.broadcast_table(serverSocket, regDict, user_name)

        elif expect == 'O':
            # offline chat
            target_name = to_split[2]
            o_msg = to_split[3]
            offline_log = target_name + "_offline_log.txt"
            o_msg = user_name + ": " + o_msg + ": " + str(time.time()) + "\n"

            with open(offline_log, 'a') as stored_txt:
                stored_txt.write(o_msg)
            self.change_status(target_name, regDict, 'offline')
            self.broadcast_table(serverSocket, regDict, user_name)
            self.send_ack(serverSocket, regDict, user_name)

            self.ping(serverSocket, regDict, target_name)
            time.sleep(.5)
            if self.ack_rcv[target_name]:
                # Then target is still alive so send error to client
                msg = "5\nserver\nError " + target_name + " still online"
                temp = regDict[user_name].split()
                new_address = (temp[0], int(temp[2]))
                serverSocket.sendto(msg.encode(), new_address)
                self.send_ack(serverSocket, regDict, user_name)

            self.ack_rcv[target_name] = False

        elif expect == 'B':
            # re-register
            entry = regDict[user_name]
            client_status = "online"
            temp = entry.rsplit(' ', 1)[0]

            client_entry = temp + " " + client_status
            regDict[user_name] = client_entry

            offline_log = user_name + "_offline_log.txt"
            try:
                # send contents of the file back
                msg = ""
                with open(offline_log, 'r') as stored_txt:
                    msg = msg + stored_txt.read()
                to_send = "3\n" + "server\n" + msg
                temp = entry.split()
                new_address = (temp[0], int(temp[2]))
                serverSocket.sendto(to_send.encode(), new_address)
            except:
                print("No offline messages for user: " + user_name)

            # build the entire table in a string from the dictionary
            table_entry = ""
            for name, entry in regDict.items():
                table_entry = table_entry + name + ": " + entry + "\n"
            # this is slightly different from broadcast table function
            # because want requesting client to get table also
            for name, entry in regDict.items():
                if "online" in entry:
                    to_send = "1\n" + "server\n" + table_entry
                    temp = entry.split()
                    new_address = (temp[0], int(temp[2]))
                    serverSocket.sendto(to_send.encode(), new_address)

            # overwrite the log with empty string
            with open(offline_log, 'w') as stored_txt:
                stored_txt.write("")

        elif expect == 'G':
            # group-chat
            # send ack back to sender user_name
            self.send_ack(serverSocket, regDict, user_name)

            # send a ping to each online client, which adds their name to the ack_rcv dictionary
            for name, entry in regDict.items():
                if "online" in entry and name != user_name:
                    self.ping(serverSocket, regDict, name)
            time.sleep(.5)
            # After waiting, toggle any clients that didn't send the ack to offline

            for name, ack in self.ack_rcv.items():
                if not ack:
                    self.change_status(name, regDict, "offline")

            # broadcast message to all online clients
            for name, entry in regDict.items():
                if "online" in entry and name != user_name:
                    to_send = "4\n" + user_name + "\n" + msg
                    temp = entry.split()
                    new_address = (temp[0], int(temp[2]))
                    serverSocket.sendto(to_send.encode(), new_address)
                if "offline" in entry and name != user_name:
                    offline_log = name + "_offline_log.txt"
                    o_msg = "Channel_Message " + name + ": " + msg + ": " + str(time.time()) + "\n"

                    with open(offline_log, 'a') as stored_txt:
                        stored_txt.write(o_msg)

            # clear the ack dictionary
            for name, ack in self.ack_rcv.items():
                self.ack_rcv[name] = False

        elif expect == "ack":
            self.ack_rcv[user_name] = True

        else:
            print("Received invalid request")

        # put all the dictionary entries into a string and write the string into file
        table_entry = ""
        for name, entry in regDict.items():
            table_entry = table_entry + name + ": " + entry + "\n"
        with open("regTable.txt", "w") as regTable:
            regTable.write(table_entry)

    def run_server(self):
        serverSocket = socket(AF_INET, SOCK_DGRAM)
        serverSocket.bind(('', self.server_port))
        print("Server is ready")
        regDict = {}

        while True:

            buf, client_address = serverSocket.recvfrom(4096)
            buf = buf.decode()
            to_split = buf.splitlines()

            handle = threading.Thread(target=self.handle_expect, args=(serverSocket, client_address, to_split, regDict))
            handle.start()
