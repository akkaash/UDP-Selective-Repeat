__author__ = 'akkaash'

import sys
import socket
import random
import shutil

globalCount = 0

M_HOSTNAME = ''
M_RECEIVING_PORT = int(sys.argv[1])
FNAME = sys.argv[2]
P = float(sys.argv[3])

M_ACK_PORT = M_RECEIVING_PORT + 1

serverReceivingSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverReceivingSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serverReceivingSocket.bind(('', M_RECEIVING_PORT))

serverAckSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverAckSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serverAckSocket.bind(('', M_ACK_PORT))
#print serverAckSocket

print M_RECEIVING_PORT, M_ACK_PORT

print 'in here'
d, a = serverReceivingSocket.recvfrom(20)
print 'done here'
CLIENT_HOSTNAME = a[0]
CLIENT_SENDING_PORT = a[1]
print str(d)
blipAck = str(d) + ':' + 'ack'
#serverReceivingSocket.sendto(blipAck, (CLIENT_HOSTNAME, CLIENT_SENDING_PORT))

d, a = serverAckSocket.recvfrom(20)
CLIENT_HOSTNAME = a[0]
CLIENT_ACK_PORT = a[1]
print str(d)
blipAck = str(d) + ':' + 'ack'
#serverAckSocket.sendto(blipAck, (CLIENT_HOSTNAME, CLIENT_ACK_PORT))

nextAckSeqNo = 0

fileDes = open(FNAME, 'wb')

d, a = serverReceivingSocket.recvfrom(20)
MSS = str(d).split(':')[1]
print 'mss = ', int(MSS)
mssAck = 'mss:ack'
serverReceivingSocket.sendto(mssAck, a)

packetList = {}

while True:
    print 'nextAckSeqNo -> ', nextAckSeqNo
    data, address = serverReceivingSocket.recvfrom(int(MSS)+3+20)
    if str(data) == 'bye':
        byePacket = 'bye:ack'
        serverAckSocket.sendto(byePacket, (CLIENT_HOSTNAME, CLIENT_ACK_PORT))
        break
    r = random.random()
    l = str(data).split(':', 3)
    ackPacket = str(l[0]) + ':' + 'ack'

    if r <= P:
        print 'Packet loss, sequence number = ', l[0]
        continue
    else:
        #print 'accepted part:', l[0]
        if int(l[0]) < nextAckSeqNo:
            print 'ack gapchi maara'
            serverAckSocket.sendto(ackPacket, (CLIENT_HOSTNAME, CLIENT_ACK_PORT))
        elif int(l[0]) == nextAckSeqNo:
            packetList[int(l[0])] = str(l[3])
            print 'ackPacket:', ackPacket
            serverAckSocket.sendto(ackPacket, (CLIENT_HOSTNAME, CLIENT_ACK_PORT))
            nextAckSeqNo += 1
            continue
        else:
            print 'out of sequence packet sending ack'
            print 'adding to dict'
            packetList[int(l[0])] = str(l[3])
            print 'added'
            print '->out of seq ack ', ackPacket
            serverAckSocket.sendto(ackPacket, (CLIENT_HOSTNAME, CLIENT_ACK_PORT))


for i in range(0, len(packetList)):
    if not packetList.has_key(i):
        print i, ' = False'
        print 'unexpected exception!'
        break
    else:
        fileDes.write(packetList[i])
