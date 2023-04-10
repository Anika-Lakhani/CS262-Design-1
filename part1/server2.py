from email import message
import socket
import random
from _thread import *
import re
import os
from turtle import update
from termcolor import colored
from database1 import create_connection1
from database2 import create_connection2
from database3 import create_connection3
import hashlib
import threading
import time


# Define Data Structures 

# KVP dictionary, where username is key and the values are the messages.
messageQueue = {}

# A list of users.
users = {}

conn = create_connection1() # Adds users from database 1 to the user list
c = conn.cursor()

c.execute("SELECT username, password_hash FROM accounts")

for row in c.fetchall():
    username = row[0]
    password_hash = row[1]
    users[username] = password_hash

c.close()
conn.close()

# A dictionary with usernames as keys and connection references as values.
conRefs = {}

# A dictionary with active in users.
active = []

# list of servers
server_addresses = [("127.0.0.1", 50052), ("127.0.0.1", 50053), ("127.0.0.1", 50051)]

# An index to keep track of the current active server
active_server_index = 0

# Threading lock to only have one leader election
election_lock = threading.Lock()

# Is this server running?
running = True

# Global variable for the session ID
with open('session_id.txt', 'r') as f:
    session_id = int(f.read().strip())

def elect_leader():
    global active_server_index
    global running

    while running:
        # Acquire the lock to perform leader election
        with election_lock:
            # Increment the active server index
            active_server_index = (active_server_index + 1) % len(server_addresses)

        # Sleep for a random time before trying the next leader election
        time.sleep(random.uniform(5, 10))


def hash_password(password):
    """Hash a password using SHA-256."""
    sha256 = hashlib.sha256()
    sha256.update(password.encode('utf-8'))
    return sha256.hexdigest()

def directMessage(connection, recipient_name, msg):
    """Send a message to the given user."""

    global session_id

    print(f"\nRequest received to send message to {recipient_name}.\n")

    updateLive()
    init_user = checkAccount(connection)

    if init_user not in active:
        msg = (colored("\nPlease log in to send a message!\n", "red"))
        return msg

    if recipient_name in users:
        sender_name = checkAccount(connection)

        with open('session_id.txt', 'r') as f:
            session_id = int(f.read().strip())

        # We are establishing a connection to our database so that we can perform a SQL query

        conn = create_connection1() # Adds to database 1
        c = conn.cursor()

        c.execute('''INSERT INTO messages (sender, recipient, message, session_id)
                    VALUES (?, ?, ?, ?)''', (sender_name, recipient_name, str(msg), session_id))
        conn.commit()
        conn.close()

        conn = create_connection2() # Adds to database 2
        c = conn.cursor()

        c.execute('''INSERT INTO messages (sender, recipient, message, session_id)
                    VALUES (?, ?, ?, ?)''', (sender_name, recipient_name, str(msg), session_id))
        conn.commit()
        conn.close()

        conn = create_connection3() # Adds to database 3
        c = conn.cursor()

        c.execute('''INSERT INTO messages (sender, recipient, message, session_id)
                    VALUES (?, ?, ?, ?)''', (sender_name, recipient_name, str(msg), session_id))
        conn.commit()
        conn.close()

        if recipient_name in active:

            msg = colored(f"\n[{sender_name}] ", "grey") + msg + "\n"
            conRefs[recipient_name].send(msg.encode('UTF-8'))
            print(f"\nMessage sent to {recipient_name}.\n")
            msg = colored(f"\nMessage sent to {recipient_name}.\n", "green")
        else:
            msg = colored(f"\n[{sender_name}] ", "grey") + msg
            if recipient_name in messageQueue:
                messageQueue[recipient_name].append(msg)
            else:
                messageQueue[recipient_name] = [msg]
            print(
                f"\nMessage will be sent to {recipient_name} after the account is online.\n")
            msg = colored(
                f"\nMessage will be delivered to {recipient_name} after the account is online.\n", "green")
        return msg

    else:
        msg = colored(
            "\nMessage failed to send! Verify recipient username.\n", "red")
        print(f"\nRequest to send message to {recipient_name} denied.\n")
        return msg

def clearQueue(recipient_name):
    """Deliver pending messages to a user."""

    while messageQueue[recipient_name]:
        conRefs[recipient_name].send(
            messageQueue[recipient_name][0].encode('UTF-8'))
        messageQueue[recipient_name].pop(0)

# Helper function to keep track of current/active users
def updateLive():
    ""
    curr_users = []
    for user in conRefs:
        try:
            conRefs[user].send("".encode('UTF-8'))
            curr_users.append(user)
        except:
            pass

    for user in active:
        if user not in curr_users:
            active.remove(user)

def verify_dupes(connection):
    """Verify if a user is already logged in when they try to log in."""

    for username in active:
        if conRefs[username] == connection:
            return True
    return False

def checkAccount(connection): 
    "Pull the account by using the connection in the active users dictionary"
    for username in conRefs:
        if conRefs[username] == connection:
            return username
    return None

def register(msg_list, connection):
    """Create an account with a password, and associate with the appropriate socket. (1|<username>|<password>)"""

    if len(msg_list) != 3:
        msg = (colored("\nInvalid arguments! Usage: 1|<username>|<password>\n", "red"))
        return msg

    updateLive()
    init_user = checkAccount(connection)

    if init_user in active:
        msg = (colored("\nPlease disconnect first!\n", "red"))
        return msg

    username = msg_list[1]
    password = msg_list[2]

    if username in users:
        print(f"\nUser {username} account creation rejected\n")
        msg = colored(f"\nAccount {username} already exists!\n", "red")
        return msg

    if not re.fullmatch("\w{2,20}", username):
        print(f"\nUser {username} account creation rejected\n")
        msg = colored(
            f"\nUsername must be alphanumeric and 2-20 characters!\n", "red")
        return msg

    users[username] = hash_password(password)

    # We are establishing a connection to our database so that we can perform a SQL query

    conn = create_connection1() # Adds new user to database 1
    c = conn.cursor()

    c.execute('''INSERT INTO accounts (username, password_hash)
                VALUES (?, ?)''', (username, hash_password(password)))
    conn.commit()
    conn.close()

    conn = create_connection2() # Adds new user to database 2
    c = conn.cursor()

    c.execute('''INSERT INTO accounts (username, password_hash)
                VALUES (?, ?)''', (username, hash_password(password)))
    conn.commit()
    conn.close()

    conn = create_connection3() # Adds new user to database 3
    c = conn.cursor()

    c.execute('''INSERT INTO accounts (username, password_hash)
                VALUES (?, ?)''', (username, hash_password(password)))
    conn.commit()
    conn.close()

    print(f"\nUser {username} account created\n")
    msg = colored(
        f"\nNew account created! User ID: {username}. Please log in.\n", "green")
    return msg

def login(msg_list, connection):
    """Check that the user is not already logged in, log in to a particular user with a password, and deliver unreceived messages if applicable."""

    if len(msg_list) != 3:
        msg = (colored("\nInvalid arguments! Usage: l|<username>|<password>\n", "red"))
        return msg

    check_duplicate = verify_dupes(connection)

    if check_duplicate == True:
        msg = (colored("\nPlease log out first!\n", "red"))
        return msg

    username = msg_list[1]
    password = msg_list[2]

    print(f"\nLogin as user {username} requested\n")

    updateLive()

    if username in active:
        print(f"\nLogin as {username} denied.\n")
        msg = colored(
            f"\nUser {username} already logged in. Please try again.\n", "red")
        return msg

    elif username not in users:
        print(f"\nLogin as {username} denied.\n")
        msg = colored(
            f"\nUser {username} does not exist. Please create an account.\n", "red")
        return msg

    elif hash_password(password) != users[username]:
        print(f"\nLogin as {username} denied.\n")
        msg = colored(
            f"\nIncorrect password. Please try again.\n", "red")
        return msg

    else:
        conRefs[username] = connection
        print(f"\nLogin as user {username} completed.\n")
        msg = colored(
            f"\nLogin successful - welcome back {username}!\n", "green")
        if username in messageQueue:
            print(f"\nDelivering pending messages to {username}.\n")
            directMessage(connection, username, colored(
                f"\nYou have pending messages! Delivering the messages now...", "green"))
            clearQueue(username)
        active.append(username)
        return msg


def delete(msg_list, connection):
    """Delete the current user's account. (d|<confirm_username>)"""

    if len(msg_list) != 2:
        msg = (colored("\nInvalid arguments! Usage: d|<confirm_username>\n", "red"))
        return msg

    username = msg_list[1]
    init_user = checkAccount(connection)

    if (init_user != username):
        msg = (colored("\nYou can only delete your own account.\n", "red"))
        return msg

    print(f"\nUser {username} requesting account deletion.\n")

    if username in users:
        del users[username]
        #users.remove(username)
        active.remove(username)
        if messageQueue.get(username):
            messageQueue.pop(username)

        # We are establishing a connection to our database so that we can perform a SQL query
        
        conn = create_connection1() # Delete user from database 1
        c = conn.cursor()

        c.execute("DELETE FROM accounts WHERE username=?", (username,))

        conn.commit()
        conn.close()

        conn = create_connection2() # Delete user from database 2
        c = conn.cursor()

        c.execute("DELETE FROM accounts WHERE username=?", (username,))

        conn.commit()
        conn.close()
        
        conn = create_connection3() # Delete user from databaase 3
        c = conn.cursor()

        c.execute("DELETE FROM accounts WHERE username=?", (username,))

        conn.commit()
        conn.close()

        print(f"\nUser {username} account deleted.\n")
        msg = colored(f"\nAccount {username} has been deleted.\n", "green")
        return msg

    else:
        return (colored("\nIncorrect username for confirmation.\n", "red"))

def userList():
    """List all of the registered users and display their status. (u)"""

    print(f'\nListing accounts\n')

    updateLive()

    if users:
        acc_str = "\n" + "\n".join([(colored(f"{u} ", "blue") +
                                     (colored("✅", "green") if u in active else ""))
                                    for u in users]) + "\n"

    else:
        acc_str = colored("\nNo existing users!\n", "red")

    return acc_str

def search(msg_list):
    """Filter accounts by a given regex."""

    print(f'\nFiltering accounts by first letter.\n')

    if len(msg_list) != 2:
        msg = (colored("\nInvalid arguments! Usage: f|<first_letter>\n", "red"))
        return msg

    updateLive()

    first_letter = msg_list[1].upper()

    if first_letter == "EASTEREGG":
        msg = "Congratulations! YOU FOUND THE EASTER EGG!\nʕ•́ᴥ•̀ʔっ♡\n"
        return msg

    if not first_letter.isalpha():
        msg = (colored("\nInvalid input! Please enter a single alphabet character.\n", "red"))
        return msg

    filtered_accounts = [user for user in users if user[0].upper() == first_letter]

    if len(filtered_accounts) > 0:
        acc_str = "\n" + "\n".join([(colored(f"{u} ", "blue") +
                                     (colored("(live)", "green") if u in active else ""))
                                    for u in filtered_accounts]) + "\n"

    else:
        acc_str = colored(f"\nNo usernames starting with {first_letter}\n", "red")

    return acc_str

# TODO: register, login, list accounts, send a message to a specific user, delete an account, filter, print all commands, handle errors
def wire_protocol(connection):
    """Main server thread that will run unless closed."""

    while True:
        # Preprocess the message by decoding it and splitting it by delimeter.
        msg = connection.recv(4096)
        msg_str = msg.decode('UTF-8')
        msg_list = msg_str.split('|')
        msg_list = [elt.strip() for elt in msg_list]
        option = msg_list[0].strip()

        # Register.
        # Usage: 1|<USERNAME>|<PASSWORD>
        if option == '1':
            msg = register(msg_list, connection)

        # Log into an account.
        # Usage: 2|<USERNAME>|<PASSWORD>
        elif option == '2':
            msg = login(msg_list, connection)

        # Delete an account
        # Usage: 3|<USERNAME>
        elif option == '3':
            msg = delete(msg_list, connection)

        # List all users and their status.
        # Usage: 4
        elif option == '4':
            msg = userList()

        # Search accounts.
        # Usage: 5|<USERNAME>
        elif option == '5':
            msg = search(msg_list)

        # History 
        # elif option == '6':
            # msg = history(msg_list, connection)

        # Send a direct message to a user.
        # Usage: dm|<recipient_username>|<message>
        elif option == 'd':
            if len(msg_list) != 3:
                msg = (colored(
                    "\nInvalid arguments! Usage: d|<recipient_username>|<message>\n", "red"))
            else:
                msg = directMessage(connection, msg_list[1], msg_list[2])

        # Print a list of all the commands.
        # Usage: h
        elif option == 'h':
            msg = "\nMessageBase -- CS 262\n"
            msg += "\n ---------"
            msg += "\n1|<USERNAME>|<PASSWORD> - Register"
            msg += "\n2|<USERNAME>|<PASSWORD> - Login"
            msg += "\n3|<USERNAME>|<PASSWORD> - Delete"
            msg += "\n4 - Display User List"
            msg += "\n5|<USERNAME> - Search for User(s)"
            msg += "\n6|Re-Generate Chat"
            msg += "\nd|<TO>|<MESSAGE> - Send Private Message"
            msg += "\nh - HELP | Display all options"
            msg = colored(msg, 'blue')

        # Handles an invalid request and lists the correct usage for the user.
        else:
            msg = "\nInvalid request, use \"h\" for usage help!\n"
            msg = colored(msg, 'red')

        # Send encoded acknowledgment to the connected client
        connection.send(msg.encode('UTF-8'))

def Main():
    global active_server_index
    global running
    global session_id

    # Start the leader election thread
    election_thread = threading.Thread(target=elect_leader)
    election_thread.start()

    ip, port = None, None  # Declare the variables outside the while loop

    # Main loop for the server to listen to client requests.
    while running:
        # Check if this server is the active server
        with election_lock:
            ip, port = server_addresses[active_server_index]  # Assign values to the variables
            if (ip, port) != server_addresses[active_server_index]:
                time.sleep(1)
                continue

        # Set IP address and local port.
        # ip, port = server_addresses[active_server_index]  # Remove this line

        # Specify the address domain and read properties of the socket.
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Connect to the server at the specified port and IP address.
        server.bind((ip, port))

        # Listen for a maximum of 100 active connections (can be adjusted).
        server.listen(100)

        print(f"Server started, listening on port {port}.\n")

        # Increment the session ID and write it back to the file
        session_id += 1
        with open('session_id.txt', 'w') as f:
            f.write(str(session_id))

        try:
            while True:
                connection, address = server.accept()
                print('\nConnected to:', address[0], ':', address[1])
                start_new_thread(wire_protocol, (connection,))
        
        except KeyboardInterrupt:
            running = False
            server.close()

    # Wait for the leader election thread to exit
    election_thread.join()


if __name__ == '__main__':
    Main()