from musicproto import *
import socket
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--cond-ip", help="Conductor IP address", nargs='?', default="0.0.0.0")
parser.add_argument("--play-ip", help="Player IP address", nargs='?', default="0.0.0.0")
parser.add_argument("--cond-port", help="Conductor TCP or UDP port", nargs='?', default=30000, type=int)
parser.add_argument("--play-port", help="Player TCP or UDP port", nargs='?', default=30001, type=int)
args = parser.parse_args()

cond_ip = args.cond_ip
play_ip = args.play_ip
cond_port = args.cond_port
play_port = args.play_port

print("""
cond_ip {}
cond_port {}
play_ip {}
play_port {}
""".format(cond_ip, cond_port,
          play_ip, play_port))

# scapy configuration to be able to send over loopback interface
conf.L3socket = L3RawSocket

# open receive socket
rx_socket = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
rx_socket.bind((cond_ip, cond_port))

# create configuration of signals for players
player_alphabet = {
  'p0': SignalAlphabet(Signal(signal=440, sigLen=100),
                      Signal(signal=460, sigLen=100),
                      Signal(signal=480, sigLen=100))
}

# create and send configuration packet to players

m = MusicProtocol(
        phy = 0xAA,
        version = 0x10,
        channel = 6,
        members = 3,
        tsDur = 300,
        appId = 1,
        sigSeq = [ s for s in player_alphabet['p0'] ]
)

m.show2()

send(IP(dst=play_ip)/UDP(sport=cond_port,dport=play_port)/m)

print("\nHint: check if player received alphabet...\n")

# listen for messages coming from players

while True:
    data, addr = rx_socket.recvfrom(1024)
    m = MusicProtocol(data)
    # TODO check if received packet is a well formed MP packet
    if True:
        print("RECEIVED PACKET:")
        m.show2()
        # print(m.sigSeq)
        # print(type(m.sigSeq))
        # for s in m.sigSeq:
        #   print(s)
        # simple application: decode what player said "in binary"
        print("Player0 said: {}\n".format(player_alphabet['p0'].decode_binary(m.sigSeq)))


