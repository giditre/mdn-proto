from musicproto import *
from time import sleep

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("capt_iface_name", help="name of the capture interface (required)")
parser.add_argument("capt_iface_mac", help="MAC address of the capture interface (required)")
parser.add_argument("player_name", help="Player name (required)")
parser.add_argument("--cond-ip", help="Conductor IP address", nargs='?', default="0.0.0.0")
parser.add_argument("--play-ip", help="Player IP address", nargs='?', default="0.0.0.0")
parser.add_argument("--cond-port", help="Conductor TCP or UDP port", nargs='?', default=30000, type=int)
parser.add_argument("--play-port", help="Player TCP or UDP port", nargs='?', default=30001, type=int)
#parser.add_argument("--ipproto", help="Transport protocol ID i.e. ip_proto", nargs='?', default=17)
args = parser.parse_args()

player_name = args.player_name
capt_iface_name = args.capt_iface_name
capt_iface_mac = args.capt_iface_mac
cond_ip = args.cond_ip
play_ip = args.play_ip
cond_port = args.cond_port
play_port = args.play_port
#ip_proto = args.ipproto

print("""
player_name {}
capt_iface_name {}
capt_iface_mac {}
cond_ip {}
cond_port {}
play_ip {}
play_port {}
""".format(player_name, capt_iface_name, capt_iface_mac,
          cond_ip, cond_port,
          play_ip, play_port))

# scapy configuration to be able to send over loopback interface
conf.L3socket = L3RawSocket

# open transmit socket
# tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# tx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
tx_socket = BroadcastUDPSocket()
print("Opened TX socket")

# # open receive socket
# cond_ip_broadcast = compute_broadcast(cond_ip, 24)
rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# # rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
# rx_socket = BroadcastUDPSocket()
rx_socket.bind((play_ip, play_port))
print("Opened RX socket on {} {}".format(play_ip, play_port))
print()

# # get configuration of signals for players from file
# all_alphabets = load_alphabets('alphabets.txt')
# player_alphabet = all_alphabets[player_name]
data, addr = rx_socket.recvfrom(4096)
m = MusicProtocol(data)
player_alphabet = m.sigSeq
print(player_alphabet)

# get apps information
app_signals = load_app_signals('applications.txt')

# input('\nPress Enter to continue...\n')

# initialize MusicProtocl packet
base_m = MusicProtocol(
        phy = 0xAA,
        version = 0x10,
        channel = 6,
        members = 3,
        tsDur = 300
)

# initialize packet counter
hhd_count = PacketCounter()

def monitor_callback(pck):
  ip_pck = pck.payload
  ip_tuple, err = extract_ip_tuple(ip_pck)
  print(ip_tuple)
  if ip_tuple[2] == 1:
    # ICMP
    icmp_pck = ip_pck.payload
    if icmp_pck.type != 8:
      return
    print('Received ICMP ECHO REQUEST packet')
    signal_index = get_signal_index(app_signals, 'TS', 'ECHO')
    # build packet to send to conductor
    m = base_m
    m.appId = app_signals[signal_index]['app_id']
    m.sigSeq = player_alphabet[signal_index]
    tx_socket.sendto(raw(m), (compute_broadcast(cond_ip, 24), cond_port))
  elif ip_tuple[2] == 6 or ip_tuple[2] == 17:
    # TCP or UDP
    print('Received {} packet'.format('TCP' if ip_tuple[2] == 6 else 'UDP'))
    transport_pck = ip_pck.payload
    hhd_count[ip_tuple] += len(transport_pck.payload)
    print(hhd_count)
    if sum(hhd_count.values()) >= 100:
      signal_index = get_signal_index(app_signals, 'HHD', 'SIREN')
      # build packet to send to conductor
      m = base_m
      m.appId = app_signals[signal_index]['app_id']
      m.sigSeq = player_alphabet[signal_index]
      tx_socket.sendto(raw(m), (compute_broadcast(cond_ip, 24), cond_port))
      hhd_count.clear()
  
  print()

print("Start packet capture...")

try:
  sniff(iface=capt_iface_name, filter="ether dst {} and (icmp or udp or tcp)".format(capt_iface_mac), prn=monitor_callback, store=False, stop_filter = lambda x: False, timeout=None)
except KeyboardInterrupt:
  print('\n')

#for tup in pck_count.keys():
#  print("Tuple {} observed {} time(s)".format(tup, pck_count[tup]))

# TODO also get additional filter from optional arguments

