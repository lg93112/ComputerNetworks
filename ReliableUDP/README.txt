1. Implementation Details:
This is a single thread implementation in basic Sender.py. But for bonus part in Sender2.py and Receiver2.py, 
I use several threads.

(1) Timer and time out:
When timeout happens, I retransmit the oldest unacknowledged packet in my slide window. Everytime I 
send or resend a packet, I will record the sent time associated with this packet in slide window. And 
whenever the non-blocking socket returns without packet, I will check the timer for oldest unacknowledged 
packet. If timeout happens, I will retrainsmit it. The reason for retrainsmitting the oldest unacknowledged 
packet rather than all N packets in my window are as follows:
1) Receiver will store out-of-order packets but only send acknowledgement for next expected in-order 
packet. Thus, the next N packets in the window might have been received by Receiver and Receiver hasn't 
received the oldest unacknowledged packet so it cannot send acknowledgement for these packets. Therefore 
we should only retransmit oldest unacknowledged packet which for sure is not received by Receiver. If we 
naively retrainsmit all N packets, then a lot of packets might have been received and it will cause 
unnecessary retransmission.
Besides, the instruction in HW says that Sender should only retransmit the oldest unacknowledged packet. 
And TA has confirmed this idea in Piazza.

(2) Acknowledgement:
My slide_window is a dictionary where the key is the sequence number and value is a list of 
[packet, acknowledged times, sent time]. The slide window sequence number is from seq_low and 
seq_high, and the size is 10 in basic sender as specified by WND_SIZE in Receiver but it will 
dynamically change due to congestion control in bonus part.
When sender non-blocking socket receives packet, it will firstly check checksum. Then it will 
see the sequence number. 
If seqnum is larger then seq_low, it means packets in range of [seq_low, seqnum) have been received by Receiver.
Seqnum is the next expected packet and we remove acknowledged packets from seq_low to seqnum-1, and move our window to 
[seqnum, seqnum+window_size]. So seq_low will be changed to seqnum and seq_high will be changed to seqnum+window_size.
If seqnum is smaller than seq_low, it means that it has been acknowledged before with received seqnum larger than its 
own seqnum and we can ignore this packet which has been deleted in our window already acknowledged.
If seqnum is eqaul to seq_low, it means that seq_low is next expected and hasn't been received. So 
we add the received acknowledged times of it. When we receive this packet three times, we retrainsmit it.
When sender non-blocking socket receives no packet, it will check the timer of oldest unacknowledged 
packet, and it will retrainsmit this packet if timed out.



2. Bonus part and Command to run:

(1)Congestion Control window size:
I implemented the congestion control adaptive window_size in Sender2. The window_size is originally 
set to 1 in slow start. When we receive a pakcet, we will check if current window size exceeds the 
threshold. If it's below it, we will double the window size as in slow start. If it's beyond it, 
we will increase 1 window as in linear growth stage. But in both cases the window size cannot 
exceed WND_SIZE(10) which is the receiver window size. 
When 3 duplicates time out happens, I use TCP Reno to cut window size to 1/2 but still >= 1.
When real time out happens, I set the window size to 1 and begin slow start again (still >= 1).
The threshold is set to WND_SIZE in initial case and it will be reduced to half in both time out conditions(still >= 1). 

(2)Adaptive time-out interval:
I use the formulas in TCP to dynamically determine the time-out interval in Sender2, which are: 
EstimatedRTT = 0.875EstimatedRTT + 0.125SampleRTT
DevRTT = 0.75DevRTT + 0.25|SampleRTT-EstimatedRTT|
TimeoutInterval = EstimatedRTT + 4*DevRTT
The original EstimatedRTT, DevRTT and TimeoutInterval will be set to 0.
Note that SampleRTT could be large, e.g 1s, due to delay. I set the TimeoutInterval to be 
TimeoutInterval = min(EstimatedRTT + 4*DevRTT, TIMEOUT(500ms)) to keep it within 500ms frame. 

Basic Sender/Receiver, part(1) and part(2) could be all tested using the command:
python Sender.py/Sender2.py Inputfile ReceiverAddress(localhost) ReceiverPort
python Receiver.py/Receiver2.py Outputfile ReceiverAddress(localhost) ReceiverPort
For example:
python Sender.py(Sender2.py) red\ and\ blue2.jpg localhost 6000
python Receiver.py(Receiver2.py) output.jpg localhost 6000

The len(sys.argv) = 4 and it indicates that we use Sender2 as only sender and Receiver2 as only 
receiver.

(3) Simultaneous send and recv:
I use three threads in both Sender2 and Receiver2: main thread, t1 and t2. In Sender2, t1 thread 
will behave as sender while t2 is originally set to None. Only if when we have len(sys.argv) > 4 will 
we use t2 as receiver. In Receiver2, t1 thread will behave as receiver while t2 is originally set to None. 
Only if when we have len(sys.argv) > 4 will we use t2 as sender.
To invoke both Sender2 and Receiver2 to send and receive simultaneously, we should use the following command:

python Sender2.py Inputfile ReceiverAddress ReceiverPort Outputfile SenderAddress SenderPort
(This Outputfile is the filename to be received for sender, and SenderAddress and SenderPort are used to create receiver_socket(local_socket))
python Receiver2.py Outputfile ReceiverAddress ReceiverPort Inputfile SenderAddress SenderPort
(This Inputfile is to the filename to be sent for receiver, and SenderAddress and SenderPort are used to send packets to)

In Sender2, I create a sender_socket binding to ('', 8000) to send packets.
In Receiver2, I create a sender_socket binding to ('', 9000) to send packets.
Thus, the port numbers for Receiver2 and Sender2 to receive file should be different respectively and also other than 8000 and 9000.

For example, I use following commands to test my Receiver2 and Sender2 for part3 bonus part:
python Sender2.py red\ and\ blue2.jpg localhost 6000 sender_out.jpg localhost 7000
python Receiver2.py output_receiver.jpg localhost 6000 corgi1.jpg localhost 7000



3. Results
Send functions in both basic Sender and Sender2 will not output anything to console. I use the 
original recv function with output in console in Receiver and Receiver2. So the only things we will see 
on the console are the information printed by recv specified in original Receiver.
For example, when we run the commands in 2.(3), we will see both Sender2 and Receiver2 will output 
results of simultaneous recv information for the file they are receiving respectively.
The average time to send and receive a jpg file of 27KB with 55 packets is 18-30 sec.





