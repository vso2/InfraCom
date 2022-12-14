from queue import Queue


def deliver_data(buffer,msg, queue: Queue, lock):
    if chr(msg) == '\0':
        message =''.join(buffer)
        with lock:
            queue.put(message)
        buffer = []
    else:
        buffer.append(chr(msg))
    return buffer


def deliver_data_client(buffer,msg):
    if chr(msg) == '\0':
        message =''.join(buffer)
        print(message)
        buffer = []
    else:
        buffer.append(chr(msg))
    return buffer
