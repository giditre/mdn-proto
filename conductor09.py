from musicproto import *
import socket
import time
import argparse
from threading import Timer, Lock
import logging
import os

import random

# set up logger to write useful information on the terminal
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# gather command line parameters fed to the script
parser = argparse.ArgumentParser()

parser.add_argument("--cond-ip", help="Conductor IP address", nargs='?', default="0.0.0.0")
parser.add_argument("--play-ip", help="Player IP address", nargs='?', default="0.0.0.0")
parser.add_argument("--cond-port", help="Conductor TCP or UDP port", nargs='?', default=30000, type=int)
parser.add_argument("--play-port", help="Player TCP or UDP port", nargs='?', default=30001, type=int)
parser.add_argument("-L", "--lease-length", help="Time in seconds for which a set of signal is assigned to a player", nargs='?', default=180, type=int)
parser.add_argument('-v', '--virtual', help="Virtual sound mode", action='store_true', required=False)

args = parser.parse_args()

# store parameters in global variables
cond_ip = args.cond_ip
play_ip = args.play_ip
cond_port = args.cond_port
play_port = args.play_port
lease_length = args.lease_length
virtual = True if args.virtual else False

logger.debug("""
cond_ip {}
cond_port {}
play_ip {}
play_port {}
lease_length {}
virtual mode {}""".format(cond_ip, cond_port,
      play_ip, play_port, lease_length,
      'YES' if virtual else 'NO'))

# scapy configuration to be able to send over loopback interface
conf.L3socket = L3RawSocket

# open transmit socket
tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# tx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
# tx_socket = BroadcastUDPSocket()
logger.info("Opened TX socket")

# open receive socket
cond_ip_broadcast = compute_broadcast(cond_ip, 24)
# rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx_socket = BroadcastUDPSocket()
rx_socket.bind((cond_ip_broadcast, cond_port))
logger.info("Opened RX socket on {} {}".format(cond_ip_broadcast, cond_port))

# initialize signal handler
### IMPORTANT: feed the constructor with the parameters required by the specific physical technology used. Look MusicProtocolSignalHandler in musicproto.py for details
signal_handler = MusicProtocolSignalHandler("WIRED", tx_socket=tx_socket, rx_socket=rx_socket, virtual=virtual)

# load mapping of signals to application, as per the text file applications.txt
app_signals = load_app_signals('applications.txt')
logger.debug('Signals {}'.format(app_signals))

# create configuration of signals (i.e. alphabets) for a player
# alphabet will start at 'base_frequency', have a gap 'gap' between consecutive symbols, every signal will have duration 'duration' in milliseconds, and the alphabet will have length'alphabet_length'
# TODO: get base frequency, gap and duration from file
def create_alphabet(base_freq=100, gap=20, duration=1000, alphabet_length=len(app_signals)):
  alphabet = []
  next_freq = base_freq
  for a in range(alphabet_length):
    freq = next_freq
    alphabet.append(Signal(signal=freq, sigLen=duration))
    next_freq = freq + gap
  return alphabet, next_freq


### setup phase
# quick outline:
# wait for at least one player to contact the conductor
# when that happens, go through the 4 steps of setup
# remember to create (random) session_id and keep track of it
# generate an alphabet for every player using the function create_alphabet
# for now, this is implemented for only 1 player (1 setup phase then listen for signals without expecting any other player to connect) then we could extend it to more players (thread in the background ready to go through setup phase for new players, while the main thread keeps listening to signals from registered players)
# create a dictionary as a means to store all session_ids of every player, associating them with their IP address

# initialize structures to store connectd players and their alphabets
# players = {<session_id>: <address>}
players = {}
player_alphabets = {}

# wait for player to contact the conductor with player hello
logger.debug("Wait for PlayerHello")
data, addr = rx_socket.recvfrom(4096)

player_hello_packet = MPSetupPlayerHello(data)
logger.debug("Received PlayerHello from {}".format(addr))

# TODO: retrieve list of phys supported by player and choose one
# for the moment just impose the default one - 0x3 WIRED
phy = 0x3

# generate session_id as a random integer between 0 and 255, avoiding existing values
session_id = random.choice([n for n in range(256) if n not in players])
players[session_id] = addr[0]

# generate and send conductor hello packet
conductor_hello_packet = MPSetupConductorHello(version=1, session=session_id, phy=phy)
tx_socket.sendto(raw(conductor_hello_packet), (players[session_id], play_port))
logger.debug("Sent ConductorHello")

# wait for reception of player channel suggestion
# logger.debug("Wait for PlayerChannel")
data, addr = rx_socket.recvfrom(4096)
player_channel_packet = MPSetupPlayerChannel(data)
logger.debug("Received PlayerChannel")

# TODO: retrieve suggested channel from player
# for the moment just impose the channel - 3 (no particular meaning)
channel = 3

# create alphabet for player
# TODO: extend for creation of multiple alphabets, feeding the function meaningful values and keeping track of next_freq for creation of following alphabet
alphabet, next_freq = create_alphabet()
logger.debug("Created alphabet {} for session {}".format(alphabet, session_id))
player_alphabets[session_id] = alphabet

# generate packet to tell the player which signals to use, and send it
conductor_signals_packet = MPSetupConductorSignals(version=1, session=session_id, phy=phy, channel=channel, sigSeq=alphabet)
tx_socket.sendto(raw(conductor_signals_packet), (players[session_id], play_port))
logger.debug("Sent Signals")

# wait for reception of ACK from player
data, addr = rx_socket.recvfrom(4096)
# TODO: check that message received is actually ACKSIG from player
logger.debug("Received ACKSIG")

### end setup phase

# listen for signals coming from players
logger.info('Start listening to players...')
#rx_socket.settimeout(None)
try:
  while True:
      signal_seq = signal_handler.receive()
      player_name = which_alphabet(player_alphabets, signal_seq)
      for s in signal_seq:
        app_signal = app_signals[player_alphabets[player_name].index(s)]
        logger.info("Player {} - app {} - {}\n".format(player_name, app_signal['app_name'], app_signal['signal']))
except KeyboardInterrupt:
  if virtual:
    exit_msg = signal_handler.quit()
    if exit_msg is not None:
      print(exit_msg)
      samples = mpvirtlib.generate_samples(exit_msg[0], exit_msg[1], 48000) 
      mpvirtlib.write_wav('virtualsound.wav', samples, 48000)
  pass

### the following code might be useful for improvements (or not)
# # get players
# players = {}
# with open('players.txt') as f:
#   for line in f:
#     splitted_line = line.strip('\n').split(':')
#     player_name = splitted_line[0]
#     player_locator = splitted_line[1]
#     players[player_name] = {'locator': player_locator}
# logger.debug(players)

#logger.debug('Alphabets {}'.format(player_alphabets))

# alphabet_lock = Lock()
# # write alphabets to file
# with alphabet_lock:
#   write_alphabets('alphabets.dat', player_alphabets)

# # send alphabets to players
# def send_alphabet(alphabets, player_name, player_locator, lease_len):
#   global play_port
#   logger.debug('Conf to {} at {} {}'.format(player_name, player_locator, play_port))
#   m = MusicProtocol(
#         phy = 0xAA,
#         version = 0x10,
#         members = len(players),
#         tsDur = lease_len,
#         appId = 0,
#         channel = int(p.replace('p', '')),
#         sigSeq = alphabets[player_name]
#   )
#   # m.show2()
#   tx_socket.sendto(raw(m), (player_locator, play_port))
#   ## reschedule execution of same function after lease_length seconds
#   #Timer(lease_length, send_alphabet, args=[alphabets, player_name, player_locator, lease_len]).start()
# 
# for p in players:
#   send_alphabet(player_alphabets, p, players[p]['locator'], lease_length)


