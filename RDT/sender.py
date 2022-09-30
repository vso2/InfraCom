import socket
from threading import Thread
from queue import Queue
import sys

from rdt import corrupt, isACK, notCorrupt, rdt_rcv, rdt_send

messageQueue = Queue()
clientPacketLength = 97
bufferSize = 100
sender_state = 0

def get_input():
    while True:
        print('\n\n\nSegunda Entrega do Projeto de Infracom - Protocolo RDT\nEscolha as seguintes opções:\n\n1- Enviar pacote numérico\n2- Enviar Mensagem de texto\n3- Enviar Pacote Corrompido\n4 - Sair\n\n')
        try:
            choice = int(input())
            if choice == 1:
                while True:
                    notFinished = True
                    while notFinished:
                        try:
                            inp = int(input('Write a integer number:  '))
                            messageQueue.put(inp)
                        except ValueError as e:
                            print('Please, insert a integer')
                            continue
                        val = input('Would you like to insert another number in queue?(Y/N)')
                        if val != 'Y' and val != 'y' :
                            notFinished = False
                    sender_thread = Thread(target = sender, args=(False,))
                    sender_thread.start()
                    sender_thread.join()
                    return
            elif choice == 2:
                while True:
                    notFinished = True
                    while notFinished:
                        try:
                            inp = input('Write your message (ascii characters only):  ')
                            [messageQueue.put(ord(x)) for x in inp ]
                            messageQueue.put(ord('\n'))
                        except ValueError as e:
                            print(e)
                            continue
                        val = input('Would you like to insert another message in queue?(Y/N)')
                        if val != 'Y' and val != 'y' :
                            notFinished = False
                    sender_thread = Thread(target = sender, args=(False,))
                    sender_thread.start()
                    sender_thread.join()
                    return
            elif choice == 3:
                while True:
                    notFinished = True
                    while notFinished:
                        try:
                            inp = int(input("Write a integer number(It's going to be corrupted):  "))
                            messageQueue.put(inp)
                        except ValueError as e:
                            print('Please, insert a integer')
                            continue
                        val = input('Would you like to insert another number in queue?(Y/N)')
                        if val != 'Y' and val != 'y' :
                            notFinished = False
                    sender_thread = Thread(target = sender, args=(True,))
                    sender_thread.start()
                    sender_thread.join()
                    return
            elif choice == 4:
                break
            else:
                print('-----Please, input a valid option-----')
        except ValueError as e:
            print('Insert a valid option')








def sender(corruptPack):

    serverAddressPort   = ("localhost", 8080)

    # states
    # 0 - Wait for call 0 from above
    # 1 - Wait for ACK 0
    # 2 - Wait for call 1 from above
    # 3 - Wait for ACK 1

    bufferSize = 100

    #Set Initial enviromental states
    sender_state = 0

    # Create a UDP socket at client side

    user = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    last_data = None
    while True:
        if sender_state == 0:
            try:
                if not messageQueue.empty():
                    data = messageQueue.get()
                    print('Sending packet and waiting for ACK 0... {}'.format(data))
                    last_data = data
                    rdt_send(user, serverAddressPort,clientPacketLength, sender_state, data,corruptPack)
                    user.settimeout(1)
                    sender_state = 1
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
                data,_ = rdt_rcv(user, bufferSize)
                if notCorrupt(data, 'client') and isACK(data, 0):
                    user.settimeout(None)
                    print('Received ACK 0'.format(last_data))
                    sender_state = 2
                else:
                    print('Something went wrong on transmission of the packet!\n','Corrupted: {}\nGOT for ACK 0:  {}\n'.format(corrupt(data), isACK(data, 0)))
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    print('TIMED OUT! RETRANSMITING LAST PACKET...')
                    rdt_send(user, serverAddressPort,clientPacketLength, sender_state, last_data, False)
            except socket.error as e:
                print (e)
                sys.exit(1)

        elif sender_state == 2:
            try:
                if not messageQueue.empty():
                    data = messageQueue.get()
                    print('Sending packet and waiting for ACK 1... {}'.format(data))
                    last_data = data
                    rdt_send(user, serverAddressPort,clientPacketLength, sender_state, data,corruptPack)
                    user.settimeout(1)
                    sender_state = 3
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
                data, _ = rdt_rcv(user, bufferSize)
                if notCorrupt(data, 'client') and isACK(data, 1):
                    user.settimeout(None)
                    print('Received ACK 1 {}'.format(last_data))
                    sender_state = 0
                else:
                    print('Something went wrong on transmission of the packet!\n','Corrupted: {}\nGOT for ACK 1:  {}\n'.format(corrupt(data), isACK(data, 1)))
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    print('TIMED OUT! RETRANSMITING LAST PACKET...')
                    rdt_send(user, serverAddressPort,clientPacketLength, sender_state, last_data, False)
            except socket.error as e:
                print (e)
                sys.exit(1)
        else:
            print('Something went wrong! Back to initial state...')
            sender_state = 0

sender_thread = Thread(target = sender)
input_thread = Thread(target = get_input)

input_thread.start()
#sender_thread.start()

"""
import socket
from threading import Thread
from queue import Queue
import sys

messageQueue = Queue()
messageQueue.put('DALE BOY')

def get_input():
    while True:
        msg = input()
        messageQueue.put(msg)


def sender():

    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocket.settimeout(1)
    serverAddressPort   = ("localhost", 8080)
    bufferSize          = 1024
    while True:
        try:
            if not messageQueue.empty():
                msgFromClient       = messageQueue.get()
                bytesToSend         = str.encode(msgFromClient)
                UDPClientSocket.sendto(bytesToSend, serverAddressPort)
            msgFromServer = UDPClientSocket.recvfrom(bufferSize)

            msg = "\nMessage from Server {}".format(msgFromServer[0])

            print(msg)
        except socket.timeout as e:
            err = e.args[0]
            if err == 'timed out':
                continue
        except socket.error as e:
            print (e)
            sys.exit(1)
            
        



sender_thread = Thread(target = sender)
input_thread = Thread(target = get_input)

input_thread.start()
sender_thread.start()"""
