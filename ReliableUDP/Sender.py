from socket import *
from utils import *
import time, struct, sys, random
import os
import math

slide_window = {} # global variable, slide window size is set to WND_SIZE in the basic sender
seq_low = 0 # global variable representing oldest unacknowledged packet seq# in slide window
seq_high = -1 # global variale representing largest packet seq# in slide window
last_chunk = 0 # global variable representing total number of packets of sent file

# This function is to add more windows when acknowledged windows are removed and leave 
# new spaces for new packets. And it's used to send the original packets
def add_window(f, sender_socket, address, port, num):
    global slide_window
    global seq_low
    global seq_high
    global last_chunk

    for i in range(num):
        try:
            chunk = f.next()
            seq_high += 1
            packet = bytes()
            if last_chunk == 0:
                packet = make_packet(seq_high, chunk, SPECIAL_OPCODE)
            elif seq_high == 0:
                packet = make_packet(seq_high, chunk, START_OPCODE)
            elif seq_high == last_chunk:
                packet = make_packet(seq_high, chunk, END_OPCODE)
            else:
                packet = make_packet(seq_high, chunk, DATA_OPCODE)
            slide_window[seq_high] = [packet, 0, time.time()]
            sender_socket.sendto(packet, (address, port))
            if last_chunk == 0 or seq_high == last_chunk:
                break
        except Exception as err:
            break

# This function is to implement non-blocking recv
def receive(sender_socket):
    try:
        message, _ = sender_socket.recvfrom(MAX_SIZE)
        return message
    except:
        return None

# This is the core send function
def send(file_name, address, port, sender_socket):
    global slide_window
    global seq_low
    global seq_high
    global last_chunk

    # set socket timeout to be 0.1s to be non-blocking. When socket receives packets,
    # handle it. When it receives no packets, it will return with None and check timer to resend oldest unacknowledged.
    sender_socket.settimeout(0.1) 
    f = read_file(file_name)
    last_chunk = int(math.ceil(os.path.getsize(file_name)*1.0/DATA_LENGTH)) - 1

    # initialize slide window and send original packets
    add_window(f, sender_socket, address, port, WND_SIZE)
    
    while slide_window:
        message = receive(sender_socket)
        if message: # when socket receives packet
            #extracting the contents of the packet, with a method from utils
            csum, rsum, seqnum, flag, data = extract_packet(message)
            # ignore invalid checksum
            if csum != rsum:
                continue
            # if seqnum is larger then seq_low, it means packets in range of [seq_low, seqnum) have been acknowledged.
            # seqnum is the next expected packet and we remove acknowledged packets and move the window starting from seqnum
            if seqnum > seq_low:
                num = 0
                oldlow = seq_low
                for seq in range(oldlow, seqnum):
                    slide_window.pop(seq)
                    seq_low += 1
                    num += 1
                add_window(f, sender_socket, address, port, num)
            # ignore delyed packet with seqnum < seq_low, which has been acknowledged before with received seqnum larger than itself
            elif seqnum < seq_low:
                continue
            # duplicate packet for seq_low = seqnum. seq_low is next expected and hasn't been acknowledged
            else:
                slide_window[seqnum][1] += 1
                if slide_window[seqnum][1] == 3:
                    sender_socket.sendto(slide_window[seqnum][0], (address, port))
                    slide_window[seqnum][2] = time.time()
                    slide_window[seqnum][1] = 0
        else:
            # when socket doesn't receive packet and return None, it will check the timer for oldest unacknowledged and resend it if timeout
            elapsed_time = time.time()-slide_window[seq_low][2]
            if  elapsed_time >= TIMEOUT:
                sender_socket.sendto(slide_window[seq_low][0], (address, port))
                slide_window[seq_low][2] = time.time()

def usage():
	print("Usage: python Sender.py <input file> <receiver address> <receiver port>")
	exit()

def main():
    if len(sys.argv) < 4:
        usage()
        sys.exit(-1)

    file_name = sys.argv[1]
    address = sys.argv[2]
    port = int(sys.argv[3])

    # sender_socket
    sender_sock = socket(AF_INET, SOCK_DGRAM)
    sender_sock.bind(('', 7000))
    
    send(file_name, address, port, sender_sock)
    
if __name__ == '__main__':
	main()