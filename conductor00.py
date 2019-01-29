from musicproto import *
import socket
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

# open receive socket
rx_socket = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
rx_socket.bind(("", src_port))

# create configuration of signals for players
player_alphabet = {
        'p0': [ (440, 100), (460, 100), (480, 100) ]
}

# create and send configuration packet to players

m = MusicProtocol(
        phy = 0xAA,
        version = 0x10,
        channel = 6,
        members = 3,
        tsDur = 300,
        appId = 1,
        sigSeq = [ Signal(signal=s, sigLen=sl)
            for s, sl in player_alphabet['p0'] ]
)

m.show2()

send(IP(dst=dst)/UDP(sport=src_port,dport=dst_port)/m)

print("\nHint: check if player received alphabet...\n")

# listen for messages coming from players

while True:
    data, addr = rx_socket.recvfrom(1024)
    m = MusicProtocol(data)
    # TODO check if received packet is a well formed MP packet
    if True:
        print("RECEIVED PACKET:")
        m.show2()
        # simple application: decode what player said "in binary"
        n = 0
        for s in m.sigSeq:
            i = player_alphabet['p0'].index((s.signal, s.sigLen))
            n += 2**i
        print("Player0 said: {}\n".format(n))


