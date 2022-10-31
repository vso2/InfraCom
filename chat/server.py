import socket
from threading import Thread
from threading import Lock
from traceback import print_tb
from rdt.rdt import corrupt, extract, has_seq0, has_seq1, isACK, make_server_packet, rdt_rcv, checksum, udt_send, unroll_server_data, notCorrupt, rdt_send
from rdt.infrastructure import broadcast,deliver_data
from queue import Queue
import sys
from ast import literal_eval


class Client:
    def __init__(self, address):
        self.buffer = []
        self.address = address
        self.server_state = 0
        self.delivery_state = 0
        self.listener_sock = ''
        self.name = ''
        self.ban_counter = 0
    
    def change_server_state(self):
        self.server_state = 1 - self.server_state

    def update_buffer(self, new_buffer):
        self.buffer = new_buffer

    def change_delivery_state(self, state):
        self.delivery_state = state

    def define_listener_sock(self,listener):
        self.listener_sock = listener

    def define_client_name(self, name):
        self.name = name
    
    def increment_ban_count(self):
        self.ban_counter = self.ban_counter + 1



def server_thread(server, client:Client,data, messages_queue,lock):
    
    
    address = client.address
    server_state = client.server_state
    buffer = client.buffer

    while True:

        userPort, serverPort, length, checksum_field, seq, msg = unroll_server_data(data)
        if server_state == 0:
            if notCorrupt(data) and has_seq0(data):
                msg = extract(data)
                buffer = deliver_data(buffer,msg,messages_queue, lock)
                client.update_buffer(buffer)
                sndpkt = make_server_packet(localPort, address[1], length,1, 0)
                udt_send(server,sndpkt, address)
                client.change_server_state()
                #print('Received packet from client {} containing {}'.format(address,msg), ', sending ACK...')
                return
            elif corrupt(data) or has_seq1(data):
                sndpkt = make_server_packet(localPort, address[1], length,1, 1)
                udt_send(server,sndpkt, address)
                print('[SERVER_THREAD 1]Something went wrong on transmission of the packet!\n ','Corrupted: {}\nNot Expected Sequence Number: {}\n'.format(corrupt(data), has_seq1(data)))
                return
        elif server_state == 1:
            if notCorrupt(data) and has_seq1(data):
                msg = extract(data)
                buffer = deliver_data(buffer,msg,messages_queue, lock)
                client.update_buffer(buffer)
                sndpkt = make_server_packet(localPort, address[1], length,1, 1)
                udt_send(server,sndpkt, address)
                client.change_server_state()
                #print('Received packet containing {}'.format(msg), ', sending ACK...')
                return
            elif corrupt(data) or has_seq0(data):
                sndpkt = make_server_packet(localPort, address[1], length,1, 0)
                udt_send(server,sndpkt, address)
                print('[SERVER_THREAD 2]Something went wrong on transmission of the packet!\n ','Corrupted: {}\nNot Expected Sequence Number: {}\n'.format(corrupt(data), has_seq0(data)))
                return



def sender(client:Client, delivery_socket:socket, message):

    serverAddressPort   = client.listener_sock
    characterQueue = Queue()
    clientPacketLength = 97
    bufferSize = 100

    print('SENDER THREAD', serverAddressPort)

    # states
    # 0 - Wait for call 0 from above
    # 1 - Wait for ACK 0
    # 2 - Wait for call 1 from above
    # 3 - Wait for ACK 1

    #Set Initial enviromental states
    sender_state = client.delivery_state
    last_data = None

    [characterQueue.put(ord(x)) for x in message]
    characterQueue.put(ord('\0'))

    print(message)

    # Create a UDP socket at client side

    while True:
        #print(serverAddressPort)
        if sender_state == 0:
            try:
                if not characterQueue.empty():
                    data = characterQueue.get()
                    #print('Sending packet and waiting for ACK 0... {}'.format(data))
                    last_data = data
                    rdt_send(delivery_socket, serverAddressPort,clientPacketLength, sender_state, data)
                    delivery_socket.settimeout(1)
                    sender_state = 1
                    client.change_delivery_state(sender_state)
                else:
                    return
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    continue
            except socket.error as e:
                print (e)
                sys.exit(1)
        elif sender_state == 1:
            try:
                data,_ = rdt_rcv(delivery_socket, bufferSize)
                #print(data)
                if notCorrupt(data, 'client') and isACK(data, 0):
                    delivery_socket.settimeout(None)
                    #print('Received ACK 0'.format(last_data))
                    sender_state = 2
                    client.change_delivery_state(sender_state)
                else:
                    print('Something went wrong on transmission of the packet!\n','Corrupted: {}\nGOT for ACK 0:  {}\n'.format(corrupt(data), isACK(data, 0)))
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    print('TIMED OUT! RETRANSMITING LAST PACKET...')
                    rdt_send(delivery_socket, serverAddressPort, clientPacketLength, sender_state, last_data)
            except socket.error as e:
                print (e)
                sys.exit(1)

        elif sender_state == 2:
            try:
                #print('sender 3th state')
                if not characterQueue.empty():
                    #print('SOME PACKET')
                    data = characterQueue.get()
                    #print('Sending packet and waiting for ACK 1... {}'.format(data))
                    last_data = data
                    rdt_send(delivery_socket, serverAddressPort,clientPacketLength, sender_state, data)
                    delivery_socket.settimeout(1)
                    sender_state = 3
                    client.change_delivery_state(sender_state)
                else: 
                    return
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    continue
            except socket.error as e:
                print (e)
                sys.exit(1)
        elif sender_state == 3:
            try:
                data, _ = rdt_rcv(delivery_socket, bufferSize)
                if notCorrupt(data, 'client') and isACK(data, 1):
                    delivery_socket.settimeout(None)
                    #print('Received ACK 1 {}'.format(last_data))
                    sender_state = 0
                    client.change_delivery_state(sender_state)
                else:
                    print('Something went wrong on transmission of the packet!\n','Corrupted: {}\nGOT for ACK 1:  {}\n'.format(corrupt(data), isACK(data, 1)))
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    print('TIMED OUT! RETRANSMITING LAST PACKET...')
                    rdt_send(delivery_socket, serverAddressPort,clientPacketLength, sender_state, last_data)
            except socket.error as e:
                print (e)
                sys.exit(1)
        else:
            print('Something went wrong! Back to initial state...')
            sender_state = 0
            client.change_delivery_state(sender_state)


def readCommand(message:str, client:Client, clients:list, bans):
    if client.name == '':
        if message.startswith('hi, meu nome eh'):
            name = message[len('hi, meu nome eh '):]
            client.define_client_name(name)
            #print(name)
            for banned_user in bans:
                if banned_user.name == name:
                    return 'user banned', 'broad'
            return '{} is connected'.format(name), 'broad'
        else:
            return 'no able to connect' , 'inbox'
    elif message == 'bye':
        name = client.name
        del clients[clients.index(client)]
        return '{} leave the room'.format(name), 'broad'
    elif message == 'list':
        val = ''
        for user in clients:
            val = val + ' ' + user.name
        return val , 'inbox'
    
    elif message.startswith('ban'):
        user_name = message[message.index('@')+1:]
        required_to_ban = int(2*len(clients)/3)
        for user in clients:
            print(user)
            if user_name == user.name:
                user.increment_ban_count()
                if user.ban_counter == required_to_ban:
                    bans.append(user)
                    del clients[clients.index(user)]
                    return 'user {} banned'.format(user.name), 'broad'
                else:
                    return '{} upvoted to ban {}'.format(client.name, user.name), 'broad'
        return 'User {} not found'.format(user_name), 'inbox'
        
    else:
        return message, 'broad'



localIP     = "localhost"
localPort   = 8080
bufferSize  = 100

server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)



delivery = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

server.bind((localIP, localPort))
delivery.bind(("localhost", 8070))
messages_received = []
clients_addresses = []
banned_addresses = []
clients = []
bans = []
num_of_messages = 0
showed_messages = 0
messageQueue = Queue()

lock = Lock()

while True:
    data, address = rdt_rcv(server, bufferSize)
    if banned_addresses.count(address) != 0:
        client = Client(address)
        delivery_thread = Thread(target=sender, args=(client, delivery, 'usuario banido, voce nao pode se conectar a sala'))
        delivery_thread.start()
        delivery_thread.join()
    elif clients_addresses.count(address) == 0:
        clients_addresses.append(address)
        client =  Client(address)
        clients.append(client)
        server_process = Thread(target=server_thread, args=(server, client, data, messageQueue,lock))
        server_process.start()
        server_process.join()
    else:
        client = clients[clients_addresses.index(address)]
        server_process = Thread(target=server_thread, args=(server, client, data, messageQueue, lock))
        server_process.start()
        server_process.join()
        if messageQueue.qsize()!= showed_messages:
            x = messageQueue.get()
            print(x)
            listener_sock = literal_eval(x[:x.find(')')+1])
            message = x[x.find(')')+1:]
            print(message)
            if client.listener_sock =='':
                client.define_listener_sock(listener_sock)
            new_message, send_type = readCommand(message,client, clients, bans)
            if send_type == 'broad':
                delivery_thread = Thread(target=sender, args=(client, delivery, new_message))
                delivery_thread.start()
                delivery_thread.join()
                for user in clients:
                    if user == client:
                        continue
                    else:
                        delivery_thread = Thread(target=sender, args=(user, delivery, new_message))
                        delivery_thread.start()
                        delivery_thread.join()
            else:
                delivery_thread = Thread(target=sender, args=(client, delivery, new_message))
                delivery_thread.start()
                delivery_thread.join()
            




