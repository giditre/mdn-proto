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
tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# tx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
# tx_socket = BroadcastUDPSocket()
print("Opened TX socket")

# open receive socket
cond_ip_broadcast = compute_broadcast(cond_ip, 24)
# rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx_socket = BroadcastUDPSocket()
rx_socket.bind((cond_ip_broadcast, cond_port))
print("Opened RX socket on {} {}".format(cond_ip_broadcast, cond_port))

print()

# get players
players = {}
with open('players.txt') as f:
  for line in f:
    splitted_line = line.strip('\n').split(':')
    player_name = splitted_line[0]
    player_locator = splitted_line[1]
    players[player_name] = {'locator': player_locator}
print(players)
print()

# # get configuration of signals for players from file
# player_alphabets = load_alphabets('alphabets.txt')
# print('Alphabets', player_alphabets)

# create configuration of signals (i.e. alphabets) for players
# TODO: get base frequency, gap, duration and alphabet length from file
base_freq = 440
gap = 20
duration = 100
alphabet_length = 2
player_alphabets = {}
next_freq = base_freq
for p in players:
  player_alphabets[p] = []
  for a in range(alphabet_length):
    freq = next_freq
    player_alphabets[p].append(Signal(signal=freq, sigLen=duration))
    next_freq = freq + gap
print('Alphabets', player_alphabets)
print()

# send alphabets to players
base_m = MusicProtocol(
        phy = 0xAA,
        version = 0x10,
        members = len(players),
        tsDur = -1,
        appId = 0
)
for p in players:
  m = base_m
  m.channel = int(p.replace('p', ''))
  m.sigSeq = player_alphabets[p]
  print(players[p])
  print(players[p]['locator'])
  tx_socket.sendto(raw(m), (players[p]['locator'], play_port))

# get apps information
app_signals = load_app_signals('applications.txt')
print('Signals', app_signals)
print()

# listen for messages coming from players
rx_socket.settimeout(None)
try:
  while True:
      data, addr = rx_socket.recvfrom(4096)
      m = MusicProtocol(data)
      # TODO check if received packet is a well formed MP packet
      if True:
          # print("RECEIVED PACKET:")
          # m.show2()
          # print(m.sigSeq)
          # print(type(m.sigSeq))
          # for s in m.sigSeq:
          #   print(s)
          # simple application: decode what player said "in binary"
          player_name = which_alphabet(player_alphabets, m.sigSeq)
          for s in m.sigSeq:
            app_signal = app_signals[player_alphabets[player_name].index(s)]
            print("Player {} - app {} - {}\n".format(player_name, app_signal['app_name'], app_signal['signal']))
except KeyboardInterrupt:
  print('\n')

