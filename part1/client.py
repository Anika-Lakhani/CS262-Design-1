import socket
import threading 
import os 
from getpass import getpass
from getpass import getuser 
import hashlib
import time
import socket
import sys
import select
from termcolor import colored
import random

leader_elected = False


def get_new_leader(servers):
    global leader_elected
    leader_index = random.randint(0, len(servers) - 1)
    leader_elected = True
    return leader_index

def connect_to_server(ip, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.connect((ip, port))
    return server

def Main():
    global leader_elected
    
    # Connect IP & Port for both servers
    servers = [("127.0.0.1", 50051), ("127.0.0.1", 50052), ("127.0.0.1", 50053)]

    # Attempt to connect to the first server
    current_server_index = 0
    while not leader_elected:
        try:
            server = connect_to_server(servers[current_server_index][0], servers[current_server_index][1])
            leader_elected = True
            print(f"Connected to Server {current_server_index + 1}")
        except ConnectionRefusedError:
            print(f"Server {current_server_index + 1} is down. Initiating leader election.")
            leader_elected = False
            current_server_index = get_new_leader(servers)

    while not leader_elected:
        current_server_index = get_new_leader(servers)
        try:
            server = connect_to_server(servers[current_server_index][0], servers[current_server_index][1])
        except ConnectionRefusedError:
            print(f"Server {current_server_index + 1} is down. Initiating leader election.")
            leader_elected = False

    print(f"Connected to Server {current_server_index + 1}")
    # Intro message

    msg = "\nMessageBase -- CS 262\n"
    msg += "\n ---------"
    msg += "\n1|<USERNAME>|<PASSWORD> - Register"
    msg += "\n2|<USERNAME>|<PASSWORD> - Login"
    msg += "\n3|<USERNAME> - Delete"
    msg += "\n4 - Display User List"
    
    msg += "\n5|<USERNAME> - Search for User(s)"
    msg += "\nd|<TO>|<MESSAGE> - Send Private Message"
    msg += "\nh - HELP | Display all options"
    msg = colored(msg, 'blue')
    print(msg)

    # Rendering initial visuals; presenting users with login options
    loggedIn = False 

    # Main loop for clients to receive and send messages to the server.
    while True:

        # List of input streams.
        sockets_list = [sys.stdin, server]

        try:
            # Initialize read sockets to process inputs from the server.
            read_sockets, _, _ = select.select(sockets_list, [], [])

            for socks in read_sockets:

                # Display messages received from the server.
                if socks == server:
                    msg = socks.recv(4096)
                    if not msg:
                        raise ConnectionError("Server connection lost.")
                    print(msg.decode('UTF-8'))

                # Send requests to the server from the client.
                else:
                    msg = sys.stdin.readline().strip()
                    server.send(msg.encode('UTF-8'))
                    data = server.recv(4096)
                    print(str(data.decode('UTF-8')))

        except (ConnectionError, socket.error):
            print("Server connection closed. Initiating leader election.")
            server.close()
            leader_elected = False
            while not leader_elected:
                current_server_index = get_new_leader(servers)
                try:
                    server = connect_to_server(servers[current_server_index][0], servers[current_server_index][1])
                except ConnectionRefusedError:
                    print(f"Server {current_server_index + 1} is down. Initiating leader election.")
                    leader_elected = False
                    
if __name__ == '__main__':
    Main()