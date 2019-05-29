from socket import *
from utils import *
import time, struct, sys, random
import os
import math
from Receiver2 import *
from threading import Thread

slide_window = {} # global variable, slide window size is dynamically changed for congestion control
seq_low = 0 # global variable representing oldest unacknowledged packet seq# in slide window
seq_high = 0 # global variale representing largest packet seq# in current window size
stored = -1 # global variable representing the largest currently packet stored in the whole window
last_chunk = 0 # global variable representing total number of packets of sent file
window_size = 1 # global variable representing window size, initially set to 1 in slow start stage
threshold = WND_SIZE # global variable representing threshold for window size from slow start to linear growth

# This function is to add more windows when acknowledged windows are removed and leave 
# new spaces for new packets. And it's used to send the original packets.
# Compared to basic Sender, it uses "stored" rather than "seq_high" due to changed window size.
def add_window(f, sender_socket, address, port, num):
    global slide_window
    global seq_low
    global seq_high
    global last_chunk
    global window_size
    global threshold
    global stored

    for i in range(num):
        try:
            chunk = f.next()
            stored += 1
            packet = bytes()
            if last_chunk == 0:
                packet = make_packet(stored, chunk, SPECIAL_OPCODE)
            elif stored == 0:
                packet = make_packet(stored, chunk, START_OPCODE)
            elif stored == last_chunk:
                packet = make_packet(stored, chunk, END_OPCODE)
            else:
                packet = make_packet(stored, chunk, DATA_OPCODE)
            slide_window[stored] = [packet, 0, time.time()]
            sender_socket.sendto(packet, (address, port))
            if last_chunk == 0 or stored == last_chunk:
                break
        except Exception as err:
            break

# Same function to implement non-blocking recv in basic sender
def receive(sender_socket):
    try:
        message, _ = sender_socket.recvfrom(MAX_SIZE)
        return message
    except:
        return None

def send(file_name, address, port, sender_socket):
    global slide_window
    global seq_low
    global seq_high
    global last_chunk
    global window_size
    global threshold
    global stored

    sender_socket.settimeout(0.1)
    f = read_file(file_name)
    last_chunk = int(math.ceil(os.path.getsize(file_name)*1.0/DATA_LENGTH)) - 1

    # Bonus part 2, calculate adaptive time out
    EstimatedRTT = 0
    DevRTT = 0
    SampleRTT = 0
    TimeoutInterval = 0
    # EstimatedRTT = 0.875EstimatedRTT + 0.125SampleRTT
    # DevRTT = 0.75DevRTT + 0.25|SampleRTT-EstimatedRTT|
    # TimeoutInterval = EstimatedRTT + 4*DevRTT

    # initialize slide window of size 1
    add_window(f, sender_socket, address, port, 1)
    
    while slide_window:
        message = receive(sender_socket)
        if message: # receive a packet
            #extracting the contents of the packet, with a method from utils
            csum, rsum, seqnum, flag, data = extract_packet(message)
            # ignore invalid checksum
            if csum != rsum:
                continue
            # if seqnum is larger then seq_low, it means packets in range of [seq_low, seqnum) have been acknowledged.
            # seqnum is the next expected packet and we remove acknowledged packets and move the window starting from seqnum
            if seqnum > seq_low:
                # calculate RTT and calculate EstimatedRTT and DevRTT using this RTT and their last values
                SampleRTT = time.time() - slide_window[seqnum-1][2]
                EstimatedRTT = 0.875*EstimatedRTT+0.125*SampleRTT
                DevRTT = 0.75*DevRTT + 0.25*abs(SampleRTT-EstimatedRTT)
                # SampleRTT could be large due to delay, so I set TimeoutInterval no larger than calculated formula or original 500ms.
                TimeoutInterval = min(EstimatedRTT + 4*DevRTT, TIMEOUT) 
                
                # Bonues part1. When it receives a packet and in slow start stage, double window size but no more that WND_SIZE(10).
                # If it's in linear growth stage, add 1 window size but also no more than WND_SIZE(10).
                if window_size < threshold:
                    window_size = window_size*2 if window_size*2 <= WND_SIZE else WND_SIZE
                else:
                    window_size = window_size+1 if window_size+1 <= WND_SIZE else WND_SIZE
                for seq in range(seq_low, seqnum):
                    slide_window.pop(seq)
                # seq_low and seq_high represent our currently concerned window, but there might be more packets in the whole window.
                seq_low = seqnum
                seq_high = seq_low+window_size-1
                if seq_low > stored:
                    add_window(f, sender_socket, address, port, seq_high-seq_low+1)
                elif seq_high > stored:
                    add_window(f, sender_socket, address, port, seq_high-stored+1)
            # ignore delyed packet with seqnum < seq_low, which has been acknowledged before with received seqnum larger than itself
            elif seqnum < seq_low:
                continue
            # duplicate packet for seq_low = seqnum. seq_low is next expected and hasn't been acknowledged
            else:
                slide_window[seqnum][1] += 1
                if slide_window[seqnum][1] == 3:
                    # 3 duplicates "timeout" use TCP RENO, 1/2 threshold and 1/2 window size
                    threshold = window_size/2 if window_size/2 >= 1 else 1
                    window_size = threshold
                    seq_high = seq_low+window_size-1
                    sender_socket.sendto(slide_window[seqnum][0], (address, port))
                    slide_window[seqnum][2] = time.time()
                    slide_window[seqnum][1] = 0     
        else:
            elapsed_time = time.time()-slide_window[seq_low][2]
            if  elapsed_time >= TimeoutInterval:
                # real timeout, window size reduce to 1, and 1/2 threshold
                threshold = window_size/2 if window_size/2 >= 1 else 1
                window_size = 1
                seq_high = seq_low
                sender_socket.sendto(slide_window[seq_low][0], (address, port))
                slide_window[seq_low][2] = time.time()

def usage_sender():
    prompt1 = "Usage: python Sender2.py Inputfile ReceiverAddress ReceiverPort"
    print(prompt1)
    prompt2 = "Or Usage: python Sender2.py Inputfile ReceiverAddress ReceiverPort Outputfile SenderAddress SenderPort"
    print(prompt2)
    exit()

def main_sender():
    if len(sys.argv) < 4:
        usage()
        sys.exit(-1)

    file_name = sys.argv[1]
    ReceiverAddress = sys.argv[2]
    ReceiverPort = int(sys.argv[3])
    # sender_socket
    sender_sock = socket(AF_INET, SOCK_DGRAM)
    sender_sock.bind(('', 8000))

    # This is for bonus part3, we create a local_socket as receiver and dump received filw to Ourputfile
    Outputfile = None
    SenderAddress = None
    local_socket = None
    # t1 thread to normally send for Sender, t2 thread to simutaneously recv
    t1 = Thread(target=send, args=(file_name, ReceiverAddress, ReceiverPort, sender_sock))
    t2 = None
    
    if len(sys.argv) > 4:
        Outputfile = sys.argv[4]
        SenderAddress = sys.argv[5]
        SenderPort = int(sys.argv[6])
        #create UDP socket to receive file on
        local_socket = socket(AF_INET, SOCK_DGRAM)
        local_socket.bind((SenderAddress, SenderPort))
        t2 = Thread(target=recv_yield, args=(Outputfile, SenderAddress, SenderPort, local_socket))

    if t2: # if sys.argv > 4, it indicates it will both be sender and receiver
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    else: # if sys.argv = 4 as usual, it indicates it will only serve as sender
        t1.start()
        t1.join()

if __name__ == '__main__':
	main_sender()