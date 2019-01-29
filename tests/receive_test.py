from musicproto import *

import socket

UDP_IP = ""
#UDP_IP = "10.0.2.15"
UDP_PORT = 30001

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.bind((UDP_IP, UDP_PORT))

while True:
    data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
    print("Received message: {}".format(data))
    #data = data.strip(bytes('\n'))

    # TODO check if packet is malformed
    # TODO check if length of packet is correct (might need to be done in the packet definition)
    # TODO check if length of signal sequence is correct (might need to be done in the packet definition)

    try:
        m = MusicProtocol(data)
        m.show2()
    except:
        print("Not a MP packet.")
