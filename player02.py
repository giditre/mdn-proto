from musicproto import *

def icmp_monitor_callback(pck):
  ip_pck = pck.payload
  ip_tuple, err = extract_ip_tuple(ip_pck)
  print(ip_tuple)
  pck_count.update([ip_tuple])

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("capt_iface_name", help="name of the capture interface (required)")
parser.add_argument("capt_iface_mac", help="MAC address of the capture interface (required)")
parser.add_argument("--cond-ip", help="Conductor IP address", nargs='?', default="0.0.0.0")
parser.add_argument("--play-ip", help="Player IP address", nargs='?', default="0.0.0.0")
parser.add_argument("--cond-port", help="Conductor TCP or UDP port", nargs='?', default=30000, type=int)
parser.add_argument("--play-port", help="Player TCP or UDP port", nargs='?', default=30001, type=int)
#parser.add_argument("--ipproto", help="Transport protocol ID i.e. ip_proto", nargs='?', default=17)
args = parser.parse_args()

capt_iface_name = args.capt_iface_name
capt_iface_mac = args.capt_iface_mac
cond_ip = args.cond_ip
play_ip = args.play_ip
cond_port = args.cond_port
play_port = args.play_port
#ip_proto = args.ipproto

print("""
capt_iface_name {}
capt_iface_mac {}
cond_ip {}
cond_port {}
play_ip {}
play_port {}
""".format(capt_iface_name, capt_iface_mac,
          cond_ip, cond_port,
          play_ip, play_port))

# scapy configuration to be able to send over loopback interface
conf.L3socket = L3RawSocket

# define configuration of signals for player
player_alphabet = SignalAlphabet()

# open receive socket
rx_socket = socket.socket(socket.AF_INET, # Internet
                          socket.SOCK_DGRAM) # UDP
#rx_socket.settimeout(0.2)
rx_socket.bind((play_ip, play_port))

while True:
    data, addr = rx_socket.recvfrom(4096)
    m = MusicProtocol(data)
    # TODO check if received packet is a well formed MP packet
    if True:
        m.show2()
        break

# extract info from configuration packet and populate the alphabet
player_alphabet.extend(m.sigSeq)

print("RECEIVED ALPHABET: {}".format(player_alphabet))

# input('\nPress Enter to continue...\n')

# initialize packet counter
pck_count = PacketCounter()

print("Start packet capture...")

try:
  while True:
    sniff(iface=capt_iface_name, filter="ether dst {} and icmp".format(capt_iface_mac), prn=icmp_monitor_callback, store=False, stop_filter = lambda x: False, timeout=5)
    total_count = sum(pck_count.values())
    if total_count > 0:
      # build packet to send to conductor
      m = MusicProtocol(
              phy = 0xAA,
              version = 0x10,
              channel = 6,
              members = 3,
              tsDur = 300,
              appId = 1,
              sigSeq = player_alphabet.encode_binary(total_count)
      )
      send(IP(dst=cond_ip)/UDP(sport=play_port,dport=cond_port)/m)
      pck_count.clear()
      print()
except KeyboardInterrupt:
  print('\n')

#for tup in pck_count.keys():
#  print("Tuple {} observed {} time(s)".format(tup, pck_count[tup]))

# TODO also get additional filter from optional arguments
