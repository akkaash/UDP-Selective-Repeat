__author__ = 'akkaash'

import sys
import socket
import threading
import signal

SERVER_HOSTNAME = sys.argv[1]  # server on this ip
SERVER_SENDING_PORT = int(sys.argv[2])  # server on this port
FILE_NAME = sys.argv[3]  # send this file
N = int(sys.argv[4])  # window size
MSS = int(sys.argv[5])  # maximum segment size of the data

SERVER_ACK_PORT = SERVER_SENDING_PORT + 1

CLIENT_SENDING_PORT = int(sys.argv[6])
CLIENT_ACK_PORT = CLIENT_SENDING_PORT + 1

timeout = False

mLock = threading.Lock()

clientSendingSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
clientSendingSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
clientSendingSocket.bind(('', CLIENT_SENDING_PORT))

clientAckSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
clientAckSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
clientAckSocket.bind(('', CLIENT_ACK_PORT))

packetList = []
nPackets = 0
sequenceNo = 0
oddFlag = 0
dataPacket = int('0101010101010101', 2)
bufferAck = []


def get_sequence_no(packet):
    return str(packet).split(':', 1)[0]


def chunks(message, n):
    for i in xrange(0, len(message), n):
        yield message[i:i+n]


def end_around_carry(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)


def checksum(msg, flag):
    s = 0
    for i in range(0, len(msg), 2):
        if flag == 0:
            w = ord(msg[i]) + (ord(msg[i+1]) << 8)
        elif flag == 1:
            w = ord('0') + (ord(msg[i]) << 8)
        s = end_around_carry(s, w)

    ret = ~s & 0xffff
    return ret

expectedAckNo = 0
receivedAckNo = -1
sentSeqNo = -1

# ------------------------------
#reading the entire file
fd = open(FILE_NAME, 'rb')
completeFile = fd.read()
fd.close()

# creating the packets..
for chunk in chunks(completeFile, MSS):
    if len(chunk) % 2 != 0:
        oddFlag = 1
    chunkChecksum = checksum(chunk, oddFlag)

    packet = str(sequenceNo) + ":" + str(chunkChecksum) + ":" + str(dataPacket) + ":" + chunk
    packetList.append(packet)
    sequenceNo += 1


maxSequenceNo = sequenceNo - 1
print 'max sequence no:', maxSequenceNo
# ------------------------------

def timeout_handler(signum, frame):
    print '---------timeout----------'
    global timeout, expectedAckNo, receivedAckNo, sentSeqNo
    timeout = True
    if receivedAckNo < maxSequenceNo:
        sentSeqNo = receivedAckNo
    signal.setitimer(signal.ITIMER_REAL, 0.9)
    #signal.alarm(2)

signal.signal(signal.SIGALRM, timeout_handler)

blip = 'blip1'
print blip
clientSendingSocket.sendto(blip, (SERVER_HOSTNAME, SERVER_SENDING_PORT))
print 'sent1'
blip = 'blip2'
print blip
clientAckSocket.sendto(blip, (SERVER_HOSTNAME, SERVER_ACK_PORT))
print 'sent2'

class AckThread(threading.Thread):
    def __init__(self, sock):
        threading.Thread.__init__(self)
        self.ack_listener_socket = sock
        print 'thread init'

    def run(self):
        print 'thread started'
        global expectedAckNo, receivedAckNo, sentSeqNo
        while True:
            data, address = self.ack_listener_socket.recvfrom(20)
            l = str(data).split(':')
            with mLock:
                if l[1] == 'ack':
                    if l[0] == 'bye':
                        print data
                        return

                    print '-> ', data

                    if int(l[0]) > expectedAckNo:
                        print 'received ack for greater sequence no.'
                        bufferAck.append(int(l[0]))
                        bufferAck.sort()
                    elif int(l[0]) == expectedAckNo:
                        print 'expectedAckNo ', int(l[0])
                        receivedAckNo += 1
                        expectedAckNo += 1
                        print 'regular update ->', receivedAckNo
                        signal.setitimer(signal.ITIMER_REAL, 0.9)

                        while bufferAck and bufferAck[0] == receivedAckNo + 1:
                            print 'getting ack from buffer->', bufferAck[0]
                            del bufferAck[0]
                            receivedAckNo += 1
                            expectedAckNo += 1
                            print 'update through buffer->', receivedAckNo
                            signal.setitimer(signal.ITIMER_REAL, 0.9)
                            bufferAck.sort()

mssPacket = 'mss:' + str(MSS)
clientSendingSocket.sendto(mssPacket, (SERVER_HOSTNAME, SERVER_SENDING_PORT))
mssAck = clientSendingSocket.recv(10)
if mssAck == 'mss:ack':
    print 'mssAck: ', mssAck

t = AckThread(clientAckSocket)
t.start()

signal.setitimer(signal.ITIMER_REAL, 0.9)


while int(receivedAckNo) < int(maxSequenceNo):
    #print 'receivedAckNo', receivedAckNo, ' maxSequence ', maxSequenceNo
    with mLock:
        while sentSeqNo - receivedAckNo < N:
            sentSeqNo += 1
            if sentSeqNo > maxSequenceNo:
                break
            print 'sending:', sentSeqNo
            d = packetList[sentSeqNo]
            clientSendingSocket.sendto(d, (SERVER_HOSTNAME, SERVER_SENDING_PORT))
            print 'sent:', sentSeqNo

    continue

endPacket = 'bye'
clientSendingSocket.sendto(endPacket, (SERVER_HOSTNAME, SERVER_SENDING_PORT))
print 'reached end'
t.join()