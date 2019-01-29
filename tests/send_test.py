from musicproto import *

import argparse

parser = argparse.ArgumentParser()
#parser.add_argument("-s", "--srcip", help="Source IP address", nargs='?', default="")
parser.add_argument("-d", "--dstip", help="Destination IP address", nargs='?', default="127.0.0.1")
parser.add_argument("--srcport", help="Source TCP or UDP port", nargs='?', default=30000)
parser.add_argument("--dstport", help="Destination TCP or UDP port", nargs='?', default=30001)
#parser.add_argument("--ipproto", help="Transport protocol ID i.e. ip_proto", nargs='?', default=17)
args = parser.parse_args()

#src = args.srcip
dst = args.dstip
src_port = args.srcport
dst_port = args.dstport
#ip_proto = args.ipproto

m = MusicProtocol(
        phy = 0xAA,
        version = 0x10,
        channel = 6,
        members = 3,
        tsDur = 300,
        appId = 1
)

signal_length = int(m.tsDur/m.members)

m.sigSeq = [
          Signal(signal=440, sigLen = signal_length),
          Signal(signal=460, sigLen = signal_length),
          Signal(signal=480, sigLen = signal_length)
]

#m.show2()

conf.L3socket = L3RawSocket # this is needed to be able to send over loopback interface

#send(IP(src=src,dst=dst,proto=ip_proto)/UDP(sport=src_port, dport=dst_port)/m)
send(IP(dst=dst)/UDP(sport=src_port,dport=dst_port)/m)

