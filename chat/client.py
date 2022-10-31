import socket
from threading import Thread
from queue import Queue
import sys
from rdt.infrastructure import deliver_data_client

from rdt.rdt import corrupt, extract, has_seq0, has_seq1, isACK, make_server_packet, notCorrupt, rdt_rcv, rdt_send, udt_send, unroll_server_data

messageQueue = Queue()
clientPacketLength = 97
bufferSize = 100
client_state = 0

class Client:
    def __init__(self, address, listener):
        self.client_state = 0
        self.server_state = 0
        self.buffer = []
        self.address = address
        self.listener = listener
    
    def update_state(self,client_state):
        self.client_state = client_state

    def update_server_state(self, server_state):
        self.server_state = server_state

    def update_buffer(self, buffer):
        self.buffer = buffer



def get_input(socket:socket, client, listener_port):
    while True:  
        notFinished = True
        while notFinished:
            try:
                inp = input('')
                [messageQueue.put(ord(x)) for x in str(listener_port) ]
                [messageQueue.put(ord(x)) for x in inp ]
                messageQueue.put(ord('\0'))
            except ValueError as e:
                print(e)
                continue
            notFinished = False
        sender_thread = Thread(target = sender, args=(client,socket))
        sender_thread.start()
        sender_thread.join()







def sender(client:Client, user):

    serverAddressPort   = ("localhost", 8080)

    # states
    # 0 - Wait for call 0 from above
    # 1 - Wait for ACK 0
    # 2 - Wait for call 1 from above
    # 3 - Wait for ACK 1

    bufferSize = 100

    #Set Initial enviromental states
    sender_state = client.client_state
    last_data = None

    # Create a UDP socket at client side

    while True:
        if sender_state == 0:
            try:
                if not messageQueue.empty():
                    data = messageQueue.get()
                    #print('Sending packet and waiting for ACK 0... {}'.format(data))
                    last_data = data
                    rdt_send(user, serverAddressPort,clientPacketLength, sender_state, data)
                    user.settimeout(1)
                    sender_state = 1
                    client.update_state(sender_state)
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
                data,aux = rdt_rcv(user, bufferSize)
                if aux[1] == 8070:
                    continue
                if notCorrupt(data, 'client') and isACK(data, 0):
                    user.settimeout(None)
                    #print('Received ACK 0'.format(last_data))
                    sender_state = 2
                    client.update_state(sender_state)
                else:
                    print('Something went wrong on transmission of the packet!\n','Corrupted: {}\nGOT for ACK 0:  {}\n'.format(corrupt(data), isACK(data, 0)))
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    #print('TIMED OUT! RETRANSMITING LAST PACKET...')
                    rdt_send(user, serverAddressPort,clientPacketLength, sender_state, last_data)
            except socket.error as e:
                print (e)
                sys.exit(1)

        elif sender_state == 2:
            try:
                if not messageQueue.empty():
                    data = messageQueue.get()
                    #print('Sending packet and waiting for ACK 1... {}'.format(data))
                    last_data = data
                    rdt_send(user, serverAddressPort,clientPacketLength, sender_state, data)
                    user.settimeout(1)
                    sender_state = 3
                    client.update_state(sender_state)
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
                data, aux = rdt_rcv(user, bufferSize)
                if aux[1] == 8070:
                    continue
                if notCorrupt(data, 'client') and isACK(data, 1):
                    user.settimeout(None)
                    #print('Received ACK 1 {}'.format(last_data))
                    sender_state = 0
                    client.update_state(sender_state)
                else:
                    print('Something went wrong on transmission of the packet!\n','Corrupted: {}\nGOT for ACK 1:  {}\n'.format(corrupt(data), isACK(data, 1)))
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    #print('TIMED OUT! RETRANSMITING LAST PACKET...')
                    rdt_send(user, serverAddressPort,clientPacketLength, sender_state, last_data)
            except socket.error as e:
                print (e)
                sys.exit(1)
        else:
            print('Something went wrong! Back to initial state...')
            sender_state = 0
            client.update_state(sender_state)




def server_thread(server, client:Client):
    
    server_state = client.server_state
    buffer = client.buffer
    client_address  = client.listener

    while True: 

        data, address = rdt_rcv(server,bufferSize)
        if address[1] == 8080:
            continue

        userPort, serverPort, length, checksum_field, seq, msg = unroll_server_data(data)
        if server_state == 0:
            if notCorrupt(data) and has_seq0(data):
                msg = extract(data)
                buffer = deliver_data_client(buffer,msg)
                client.update_buffer(buffer)
                sndpkt = make_server_packet(client_address[1], address[1], length,1, 0)
                udt_send(server,sndpkt, address)
                server_state = 1
                client.update_server_state(server_state)
                #print('Received packet from client {} containing {}'.format(address,msg), ', sending ACK...')
            elif corrupt(data) or has_seq1(data):
                sndpkt = make_server_packet(client_address[1], address[1], length,1, 1)
                udt_send(server,sndpkt, address)
                #print('Something went wrong on transmission of the packet!\n ','Corrupted: {}\nNot Expected Sequence Number: {}\n'.format(corrupt(data), has_seq1(data)))
        elif server_state == 1:
            if notCorrupt(data) and has_seq1(data):
                msg = extract(data)
                buffer = deliver_data_client(buffer,msg)
                client.update_buffer(buffer)
                sndpkt = make_server_packet(client_address[1], address[1], length,1, 1)
                udt_send(server,sndpkt, address)
                server_state = 0
                client.update_server_state(server_state)
                #print('Received packet containing {}'.format(msg), ', sending ACK...')
            elif corrupt(data) or has_seq0(data):
                sndpkt = make_server_packet(client_address[1], address[1], length,1, 0)
                udt_send(server,sndpkt, address)
                #print('Something went wrong on transmission of the packet!\n ','Corrupted: {}\nNot Expected Sequence Number: {}\n'.format(corrupt(data), has_seq0(data)))



user = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

user.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT , 1)
user.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

user.bind(('localhost',0))

listener = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT , 1)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

listener.bind(('localhost',0))

client = Client(user.getsockname(),listener.getsockname())


input_thread = Thread(target = get_input, args=(user,client,listener.getsockname()))
listen_thread = Thread(target = server_thread, args=(listener,client))

input_thread.start()
listen_thread.start()
