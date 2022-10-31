import socket
from rdt import corrupt, deliver_data, extract, has_seq0, has_seq1, make_server_packet, rdt_rcv, checksum, udt_send, unroll_server_data, notCorrupt

localIP     = "localhost"
localPort   = 8080
bufferSize  = 100

buffer = []
# Create a datagram socket
server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind to address and ip

server.bind((localIP, localPort))

print("UDP server up and listening")

#states

states = [0,1]

#Initial state and seq
server_state = 0

#env variables
online = True


# Listen for incoming datagrams

while online:

    data, address = rdt_rcv(server, bufferSize)

    userPort, serverPort, length, checksum_field, seq, msg = unroll_server_data(data)
    if server_state == 0:
        if notCorrupt(data) and has_seq0(data):
            msg = extract(data)
            buffer = deliver_data(buffer,msg)
            sndpkt = make_server_packet(localPort, address[1], length,1, 0)
            udt_send(server,sndpkt, address)
            server_state  = 1
            print('Received packet containing {}, buffer: {}'.format(msg, buffer), ', sending ACK...')
        elif corrupt(data) or has_seq1(data):
            sndpkt = make_server_packet(localPort, address[1], length,1, 1)
            udt_send(server,sndpkt, address)
            print('Something went wrong on transmission of the packet!\n ','Corrupted: {}\nNot Expected Sequence Number: {}\n'.format(corrupt(data), has_seq1(data)))
    elif server_state == 1:
        if notCorrupt(data) and has_seq1(data):
            msg = extract(data)
            buffer = deliver_data(buffer,msg)
            sndpkt = make_server_packet(localPort, address[1], length,1, 1)
            udt_send(server,sndpkt, address)
            server_state  = 0
            print('Received packet containing {}, buffer: {}'.format(msg, buffer), ', sending ACK...')
        elif corrupt(data) or has_seq0(data):
            sndpkt = make_server_packet(localPort, address[1], length,1, 0)
            udt_send(server,sndpkt, address)
            print('Something went wrong on transmission of the packet!\n ','Corrupted: {}\nNot Expected Sequence Number: {}\n'.format(corrupt(data), has_seq0(data)))

