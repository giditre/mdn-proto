from musicproto import *
import socket
import time
import argparse

parser = argparse.ArgumentParser()
#parser.add_argument("-s", "--srcip", help="Source IP address", nargs='?', default="")
parser.add_argument("-d", "--dstip", help="Destination IP address", nargs='?', default="127.0.0.1")
parser.add_argument("--srcport", help="Source TCP or UDP port", nargs='?', default=30000, type=int)
parser.add_argument("--dstport", help="Destination TCP or UDP port", nargs='?', default=30001, type=int)
#parser.add_argument("--ipproto", help="Transport protocol ID i.e. ip_proto", nargs='?', default=17)
args = parser.parse_args()

#src = args.srcip
dst = args.dstip
src_port = args.srcport
dst_port = args.dstport
#ip_proto = args.ipproto

# scapy configuration to be able to send over loopback interface
conf.L3socket = L3RawSocket

# define configuration of signals for player
player_alphabet = []

# open receive socket
rx_socket = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
#rx_socket.settimeout(0.2)
rx_socket.bind(("", src_port))

while True:
    data, addr = rx_socket.recvfrom(1024)
    m = MusicProtocol(data)
    # TODO check if received packet is a well formed MP packet
    if True:
        m.show2()
        break

# extract info from configuration packet and populate the dictionary

for s in m.sigSeq:
    player_alphabet.append((s.signal, s.sigLen))

print("RECEIVED ALPHABET: {}".format(player_alphabet))

time.sleep(5)

#print()
#input('Press Enter to continue...')
#print()

# simple application: send a binary-encoded number increasing it every time

# the highest number we can transmit is 2 to the power of the length of the alphabet
max_count = 2**len(player_alphabet)

for count in range(1, max_count):

    # convert count in binary
    b_count = "{:b}".format(count).zfill(len(player_alphabet))[::-1]

    signal_sequence = []
    for i in range(len(b_count)):
        if b_count[i] == '1':
            signal_sequence.append(Signal(signal=player_alphabet[i][0], sigLen=player_alphabet[i][1]))

    # build packet to send to conductor
    m = MusicProtocol(
            phy = 0xAA,
            version = 0x10,
            channel = 6,
            members = 3,
            tsDur = 300,
            appId = 1,
            sigSeq = signal_sequence
    )

    m.show2()

    send(IP(dst=dst)/UDP(sport=src_port,dport=dst_port)/m)

    time.sleep(1)

