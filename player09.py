from musicproto import *
from time import sleep
from threading import Thread
import argparse
import os

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[ %(asctime)s ][ %(levelname)s ] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

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

logger.debug("""
player_name {}
capt_iface_name {}
capt_iface_mac {}
cond_ip {}
cond_port {}
play_ip {}
play_port {}""".format(player_name, capt_iface_name, capt_iface_mac,
                    cond_ip, cond_port,
                    play_ip, play_port))

# scapy configuration to be able to send over loopback interface
conf.L3socket = L3RawSocket

# open transmit socket
# tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# tx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
tx_socket = BroadcastUDPSocket()
logger.debug("Opened TX socket")

# # open receive socket
# cond_ip_broadcast = compute_broadcast(cond_ip, 24)
rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# # rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
# rx_socket = BroadcastUDPSocket()
rx_socket.bind((play_ip, play_port))
logger.debug("Opened RX socket on {} {}".format(play_ip, play_port))

# initialize signal handler
signal_handler = MusicProtocolSignalHandler("WIRED", tx_socket=tx_socket, rx_socket=rx_socket)

### setup phase ("handshake")
# send player hello specifying version and supported phys
player_hello_packet = MPSetupPlayerHello(version=1, phy=[0x3])
tx_socket.sendto(raw(player_hello_packet), (compute_broadcast(cond_ip, 24), cond_port))
logger.debug("Sent PlayerHello")
# wait for reception of conductor hello
data, addr = rx_socket.recvfrom(4096)
conductor_hello_packet = MPSetupConductorHello(data)
logger.debug("Received ConductorHello")
# TODO check that type of packet received is correct, that phy is supported, and store session_id and phy
phy = conductor_hello_packet.phy
session_id = conductor_hello_packet.session
# send player channel suggestion
player_channel_packet = MPSetupPlayerChannel(version=1, session=session_id, phy=phy, channel=1)
tx_socket.sendto(raw(player_channel_packet), (compute_broadcast(cond_ip, 24), cond_port))
logger.debug("Sent PlayerChannel")
# wait for reception of signals from conductor
data, addr = rx_socket.recvfrom(4096)
conductor_signals_packet = MPSetupConductorSignals(data)
logger.debug("Received ConductorSignals")
# TODO check that receive packet has correct type, sigSeq is not empty
player_alphabet = conductor_signals_packet.sigSeq
# send ACK for signals
player_signals_ack_packet = MPSetupPlayerSignalsACK(version=1, session=session_id)
tx_socket.sendto(raw(player_signals_ack_packet), (compute_broadcast(cond_ip, 24), cond_port))
logger.debug("Sent ACKSIG")
### end setup phase


class alphabetThread(Thread):
  def __init__(self, socket, alphabet=None):
    super().__init__()
    self.rx_socket = socket
    self.alphabet = alphabet
    self.name = None
    self.lease_length = None
    self.changed = False
  def run(self):
    while True:
      data, addr = self.rx_socket.recvfrom(4096)
      m = MusicProtocol(data)
      if m.sigSeq != self.alphabet:
        if self.alphabet is not None:
          self.changed = True
        self.alphabet = m.sigSeq
        self.name = m.channel
        self.lease_length = m.tsDur
  def get(self):
    self.changed = False
    return self.alphabet
  def is_changed(self):
    if self.changed:
      return True
    else:
      return False

# get configuration of signals for players from conductor
alphabet_thread = alphabetThread(rx_socket, alphabet=player_alphabet)
alphabet_thread.start()

# player_alphabet = alphabet_thread.get()
# while not player_alphabet is not None:
#   sleep(0.5)
#   player_alphabet = alphabet_thread.get()

logger.debug('Received alphabet: {}'.format(player_alphabet))

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

# initialize counters
hhd_count = PacketCounter()
dm_count = PacketCounter()

def monitor_callback(pck):
  ip_pck = pck.payload
  ip_tuple, err = extract_ip_tuple(ip_pck)
  logger.debug(ip_tuple)
  if ip_tuple[2] == 1:
    # ICMP
    icmp_pck = ip_pck.payload
    if icmp_pck.type != 8:
      return
    logger.debug('Received ICMP ECHO REQUEST packet')
    signal_index = get_signal_index(app_signals, 'TS', 'ECHO')
    signal_handler.send(player_alphabet[signal_index], (compute_broadcast(cond_ip, 24), cond_port))
  elif ip_tuple[2] == 6 or ip_tuple[2] == 17:
    # TCP or UDP
    logger.debug('Received {} packet'.format('TCP' if ip_tuple[2] == 6 else 'UDP'))
    transport_pck = ip_pck.payload
    hhd_count[ip_tuple] += len(transport_pck.payload)
    logger.debug(hhd_count)
    if sum(hhd_count.values()) >= 100:
      signal_index = get_signal_index(app_signals, 'HHD', 'ALARM')
      signal_handler.send(player_alphabet[signal_index], (compute_broadcast(cond_ip, 24), cond_port))
      hhd_count.clear()
  # DDoS monitoring
  dm_count.update([ip_tuple])
  # TODO: get number from elsewhere
  if len(dm_count) > 3:
    logger.debug(dm_count)
    signal_index = get_signal_index(app_signals, 'DM', 'ALARM')
    signal_handler.send(player_alphabet[signal_index], (compute_broadcast(cond_ip, 24), cond_port))
    dm_count.clear()

logger.info("Start packet capture...")

while True:
  try:
    sniff(iface=capt_iface_name, filter="ether dst {} and (icmp or udp or tcp)".format(capt_iface_mac), prn=monitor_callback, store=False, stop_filter = lambda x: False, timeout=5)
    if alphabet_thread.is_changed():
      player_alphabet = alphabet_thread.get()
      logger.info('New alphabet: {}'.format(player_alphabet))
  except KeyboardInterrupt:
    break

#for tup in pck_count.keys():
#  logger.debug("Tuple {} observed {} time(s)".format(tup, pck_count[tup]))

# TODO also get additional filter from optional arguments

