import socket
from traceback import print_tb

def rdt_rcv(socket, length):
    return socket.recvfrom(length)

def ones_complement(n, size):
    comp = n ^ ((1 << size) - 1)
    return '0b{0:0{1}b}'.format(comp, size)

def checksum(sourcePort, destPort, length):
    sum_of_ports = bin(sourcePort + destPort)[2:].zfill(16)
    if len(sum_of_ports) > 16:
        sum_of_ports = sum_of_ports[1:17]
        sum_of_ports = bin(int(sum_of_ports, 2) + 1)[2:].zfill(16)
    total = bin(int(sum_of_ports, 2) + length)[2:].zfill(16)
    if len(total) > 16:
        total = total[1:17]
        total = bin(int(total, 2) + 1)[2:].zfill(16)
    checksum = ones_complement(int(total, 2), 16)[2:]
    return int(checksum, 2)

def unroll_server_data(data):
    sourcePort = int(data[0:16], 2)
    destPort = int(data[16:32], 2)
    length = int(data[32:48], 2)
    checksum_field = int(data[48:64], 2)
    seq = int(data[64:65], 2)
    msg = int(data[65:97], 2)


    return sourcePort, destPort, length, checksum_field, seq, msg

def unroll_client_data(data):
    serverSourcePort = int(data[0:16], 2)
    serverDestPort = int(data[16:32], 2)
    serverLength = int(data[32:48], 2)
    serverAck = int(data[48:49], 2)
    serverSeq = int(data[49:50], 2)
    serverChecksum = int(data[50:66], 2)

    return serverSourcePort, serverDestPort, serverLength, serverAck, serverSeq, serverChecksum


def notCorrupt(data, user = 'server'):
    if user == 'server':
        sourcePort, destPort, length, checksum_field, seq, msg = unroll_server_data(data)
    else:
        sourcePort, destPort, length, ack, seq, checksum_field = unroll_client_data(data)
    calculated_checksum = checksum(sourcePort, destPort, length)
    if calculated_checksum == checksum_field:
        return True
    return False

def has_seq0(data):
    sourcePort, destPort, length, checksum_field, seq, msg= unroll_server_data(data)
    if seq == 0:
        return True
    return False

def has_seq1(data):
    sourcePort, destPort, length, checksum_field, seq, msg = unroll_server_data(data)
    if seq == 1:
        return True
    return False

def corrupt(data):
    return not notCorrupt(data)

def extract(data):
    return int(data[65:97], 2)

def deliver_data(buffer,msg):
    if chr(msg) == '\n':
        print(''.join(buffer))
        buffer = []
    else:
        buffer.append(chr(msg))
    return buffer

def make_server_packet(sourcePort, destPort, length, ack, seq):
    checksum_field = checksum(sourcePort, destPort, length)
    pacote = bin(sourcePort)[2:].zfill(16) + bin(destPort)[2:].zfill(16) + bin(length)[2:].zfill(16) + bin(ack)[2:].zfill(1) + bin(seq)[2:].zfill(1) + bin(checksum_field)[2:].zfill(16)
    return pacote.encode()

def make_client_packet(sourcePort, destPort, length, checksum_field, seq, msg):
    pacote = bin(sourcePort)[2:].zfill(16) + bin(destPort)[2:].zfill(16) + bin(length)[2:].zfill(16) + bin(
        checksum_field)[2:].zfill(16) + bin(seq)[2:].zfill(1) + bin(msg)[2:].zfill(32)
    return pacote.encode()

def udt_send(socket, bytes, address):
    return socket.sendto(bytes, address)

def rdt_send(socket,address,length, state, data, corruptedPacket):
    sourcePort = socket.getsockname()[1]
    destPort = address[1]
    checksum_field = checksum(sourcePort,destPort,length)
    if corruptedPacket == True:
        checksum_field = checksum_field + 1
    seq = 0
    if state == 0 or state == 1:
        seq = 0
    else:
        seq = 1
    sndpkt = make_client_packet(sourcePort, destPort, length,checksum_field, seq, data)
    udt_send(socket,sndpkt, address)

def isACK(data, expected_seq):
    serverAck = int(data[48:49], 2)
    serverSeq = int(data[49:50], 2)
    if serverAck ==1 and serverSeq == expected_seq:
        return True
    return False

