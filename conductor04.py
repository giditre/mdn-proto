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

# open transmit socket
# tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# tx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
tx_socket = BroadcastUDPSocket()
print("Opened TX socket")

# open receive socket
cond_ip_broadcast = compute_broadcast(cond_ip, 24)
# rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx_socket = BroadcastUDPSocket()
rx_socket.bind((cond_ip_broadcast, cond_port))
print("Opened RX socket on {} {}".format(cond_ip_broadcast, cond_port))

print()

alphabet_length = 3
base_signal = 440
gap = 20
signal_length = 100

def gen_alphabet(player_no):
  global alphabet_length
  global base_signal
  global gap
  global signal_length

  sa = SignalAlphabet()
  for i in range(alphabet_length):
    sa.append(Signal(signal=base_signal+player_no*alphabet_length*gap+i*gap, sigLen=signal_length))
  return sa 

# create configuration of signals for players
# player_alphabet = {
#   'p0': SignalAlphabet(Signal(signal=440, sigLen=100),
#                       Signal(signal=460, sigLen=100),
#                       Signal(signal=480, sigLen=100))
# }
player_alphabet = {
  'p0': gen_alphabet(0),
  'p1': gen_alphabet(1),
  'p2': gen_alphabet(2)
}

print(player_alphabet)

player_count = 0

rx_socket.settimeout(2)

# listen for beacons
while True:
  data, addr = rx_socket.recvfrom(4096)
  if data:
    d = MusicProtocol(data)
    #d.show2()
    #input()
    if d.sigSeq[0].signal==100:
      # received beacon
      # create and send configuration packet to players
      player_name = 'p{}'.format(player_count)
      player_alphabet[player_name] = gen_alphabet(player_count)
      m = MusicProtocol(
              phy = 0xAA,
              version = 0x10,
              channel = 6,
              members = 3,
              tsDur = 300,
              appId = 1,
              sigSeq = [ s for s in player_alphabet[player_name] ]
      )
      m.show2()
      tx_socket.sendto(raw(m), (cond_ip_broadcast, cond_port))
      print("\nHint: check if player received alphabet...\n")
      player_count += 1
  else:
    break

# listen for messages coming from players
rx_socket.settimeout(None)
while True:
    data, addr = rx_socket.recvfrom(4096)
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
        player_name = which_alphabet(player_alphabet, m.sigSeq)
        print("Player {} said: {}\n".format(player_name, player_alphabet[player_name].decode_binary(m.sigSeq)))

