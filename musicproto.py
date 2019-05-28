from scapy.all import *
from collections import Counter
from ipaddress import IPv4Address, IPv4Network
import socket
from sys import stderr
from threading import Lock

import mpsoundlib
import mpvirtlib


def print_err(*args, **kwargs):
  kwargs['file'] = stderr
  print(*args, **kwargs)

class MPSetupError(Exception):
  """Raised if problems in the setup phase"""
  pass

class MPReceiveTimeoutError(Exception):
  """Raised when the receive function incurs in the timeout"""
  pass


class Signal(Packet):
    name = "SignalPacket"
    fields_desc = [
            ShortField("signal", 440),
            ShortField("sigLen", 1000)
    ]

    def extract_padding(self, s):
        return '', s

    def __str__(self):
      return ', '.join(["{}={}".format(fname, fvalue) for fname, fvalue in self.__class__(raw(self)).fields.items()])

# 8 bit field
types = {
  10: "Setup Player Hello",
  11: "Setup Conductor Hello",
  12: "Setup Player Channel Suggestion",
  13: "Setup Conductor Signal Assignment",
  14: "Setup Signal ACK from Player",
  20: "MAC Policy Change from Conductor",
  21: "MAC Policy Change ACK from Player",
  30: "Close from Conductor",
  31: "Close ACK from Player"
}

# 4 bit field
phys = {
  0:"UNSPECIFIED",
  0xA:"AUDIO",
  1:"WIFI",
  2:"BLUETOOTH",
  3:"WIRED",
  4:"VIBRATION"
}

applications = {
  0:"UNSPECIFIED",
  1:"HHD",
  2:"TS"
}


class MPSetupPlayerHello(Packet):
  name = "MPSetupPlayerHelloPacket"
  fields_desc = [
    ByteField("version", 0),
    ByteField("session", 0),
    ByteEnumField("type", 10, types),
    FieldLenField("len", None, count_of="phy"),
    FieldListField("phy", 0, ByteEnumField("phy", 0, phys), count_from=lambda pkt:pkt.len)
  ]

  def post_build(self, p, pay):
    p += pay
    if self.len is None:
        p = p[:3] + struct.pack("!H", len(p)) + p[5:]
    return p
    

class MPSetupConductorHello(Packet):
  name = "MPSetupConductorHelloPacket"
  fields_desc = [
    ByteField("version", 0),
    ByteField("session", 0),
    ByteEnumField("type", 11, types),
    ByteEnumField("phy", 0, phys)
  ]


class MPSetupPlayerChannel(Packet):
  name = "MPSetupPlayerChannelPacket"
  fields_desc = [
    ByteField("version", 0),
    ByteField("session", 0),
    ByteEnumField("type", 12, types),
    ByteEnumField("phy", 0, phys),
    ByteField("channel", 0) 
  ]


class MPSetupConductorSignals(Packet):
  name = "MPSetupConductorSignalsPacket"
  fields_desc = [
    ByteField("version", 0),
    ByteField("session", 0),
    ByteEnumField("type", 13, types),
    ShortField("len", None),
    ByteEnumField("phy", 0, phys),
    ByteField("channel", 0),
    FieldLenField("sigSeqLen", None, count_of='sigSeq'),
    PacketListField('sigSeq', None, Signal, count_from=lambda pkt:pkt.sigSeqLen)
  ]

  def post_build(self, p, pay):
    p += pay
    if self.len is None:
        p = p[:3] + struct.pack("!H", len(p)) + p[5:]
    return p


class MPSetupPlayerSignalsACK(Packet):
  name = "MPClosePlayer"
  fields_desc = [
    ByteField("version", 0),
    ByteField("session", 0),
    ByteEnumField("type", 14, types)
  ]


class MPCloseConductor(Packet):
  name = "MPCloseConductor"
  fields_desc = [
    ByteField("version", 0),
    ByteField("session", 0),
    ByteEnumField("type", 30, types),
    ByteEnumField("phy", 0, phys),
    ByteField("channel", 0)
  ]


class MPClosePlayer(Packet):
  name = "MPClosePlayer"
  fields_desc = [
    ByteField("version", 0),
    ByteField("session", 0),
    ByteEnumField("type", 31, types)
  ]



class MusicProtocol(Packet):
    name = "MusicProtocolPacket"
    fields_desc = [
        ByteEnumField("phy", 0, phys),
        XByteField("version", 0),
        ShortField("len", None),
        ByteField("channel", 0),
        ShortField("members", 1),
        ShortField("tsDur", 5000),
        ByteEnumField("appId", 0, applications),
        FieldLenField("sigSeqLen", None, count_of='sigSeq'),
        PacketListField('sigSeq', None, Signal, count_from=lambda pkt:pkt.sigSeqLen)
    ]

    def post_build(self, p, pay):
        p += pay
        if self.len is None:
            # basically we are inserting the length by overwriting the relevant bytes n the packet with the hex version of the length of the packet
            p = p[:2] + struct.pack("!H", len(p)) + p[4:]
        return p

def load_app_signals(fname):
  signals = []
  with open(fname) as f:
    for line in f:
      line = line.strip('\n').strip()

      splitted_line = line.split(':')
      app_info = splitted_line[0]
      app_signals = splitted_line[1]

      splitted_app_info = app_info.split('/')
      app_id = splitted_app_info[0]
      app_name = splitted_app_info[1]
      app_descr = splitted_app_info[2]

      splitted_app_signals = app_signals.split(',')

      for s in splitted_app_signals:
        signals.append({
          "app_id": int(app_id),
          "app_name": app_name,
          "app_descr": app_descr,
          "signal": s
        })
  return signals

def get_signal_index(signals, app_name, signal_name):
  i = None
  for s in signals:
    if s['app_name'] == app_name and s['signal'] == signal_name:
      i = signals.index(s)
      break
  if i is not None:
    return i
  else:
    raise KeyError('Signal {} of app {} not found.'.format(signal_name, app_name))

class SignalSequence(list):
  def __init__(self, *args):
    super().__init__()
    self.extend(args)

  def __str__(self):
    if not self:
      return super().__str__()
    return '; '.join(["{}".format(s) for s in self])

  def loads(self, line):
    # supposes line is formed like this:
    # signal,sigLen;signal,sigLen[; [...]]
    for s in line.split(';'):
      signal = int(s.split(',')[0])
      sigLen = int(s.split(',')[1])
      self.append(Signal(signal=signal, sigLen=sigLen))

class SignalAlphabet(SignalSequence):

  def __str__(self):
    if not self:
      return super().__str__()
    return '; '.join(["{}: {}".format(self.index(s), s) for s in self])

  def encode_binary(self, n):
    if n >= 2**len(self):
      raise ValueError("impossible to encode_binary value {} with just {} symbols in the alphabet.".format(n, len(self)))
    binary_n_reversed = '{:b}'.format(n).zfill(len(self))[::-1]
    signal_sequence = SignalSequence()
    for i in range(len(binary_n_reversed)):
      if binary_n_reversed[i] == '1':
        signal_sequence.append(self[i])
    return signal_sequence

  def decode_binary(self, signal_sequence):
    # if not isinstance(signal_sequence, SignalSequence):
    #   if isinstance(signal_sequence, list):
    #     signal_sequence = SignalSequence(signal_sequence)
    #   else:
    #     raise TypeError("impossible to decode object of type {}".format(type(signal_sequence)))
    if not all(s in self for s in signal_sequence):
      debug_msg = "The rx sequence: {}\n".format(signal_sequence)
      debug_msg += "The alphabet: {}\n".format(self)
      for s in signal_sequence:
        debug_msg += "signal {} {} in the alphabet\n".format(s, "is" if s in self else "is NOT")
      raise ValueError(debug_msg + "signal sequence contains signals not belonging to this alphabet.")
    n = 0
    for s in signal_sequence:
      n += 2**self.index(s)
    return n    

def which_alphabet(alphabet_dict, sign_seq):
  # input must be a dictionary of alphabets in the form {'alph_name': SignalAlphabet}
  if not isinstance(alphabet_dict, dict):
    raise TypeError
  for alph_name, sign_alph in alphabet_dict.items():
      if all(s in sign_alph for s in sign_seq):
        return alph_name
  # arriving here means no alphabet contained all signal in the sequence
  return None

def load_alphabets(fname):
  alphabets = {}
  with open(fname) as f:
    for n, line in enumerate(f):
      if ':' in line:
        splitted_line = line.split(':')
        alph_name = splitted_line[0]
        alph_content = splitted_line[1]
      else:
        alph_name = 'a{}'.format(n)
        alph_content = line
      alph = SignalAlphabet()
      alph.loads(alph_content)
      alphabets[alph_name] = alph
  return alphabets

def write_alphabets(fname, alphabets):
  with open(fname, 'w') as f:
    for p in alphabets:
      f.write('{}:'.format(p))
      for i, s in enumerate(alphabets[p]):
        f.write('{},{}'.format(s.signal, s.sigLen))
        if i != len(alphabets[p])-1:
          f.write(';')
        else:
          f.write('\n')

def compute_broadcast(addr, netmask):
  # input must be an IPv4 address and a netmask as int number of bits
  if not isinstance(addr, IPv4Address):
    addr = IPv4Address(addr)
  hostmask = 32 - netmask
  net = IPv4Network(str(IPv4Address(int.from_bytes(addr.packed, byteorder='big')>>hostmask<<hostmask)) + '/' + str(netmask))
  return str(net.broadcast_address)

#def is_ipv4_address(addr):
#  a = addr.split('.')
#  if len(a) != 4:
#      return False
#  for x in a:
#      if not x.isdigit():
#          return False
#      i = int(x)
#      if i < 0 or i > 255:
#          return False
#  return True

def is_ipv4_address(addr):
  try:
    a = IPv4Address(addr)
  except ValueError:
    return False
  return True

def extract_ip_tuple(packet):
  if not isinstance(packet, IP):
    return None, "Cannot extract tuple from non-IP packet."

  if isinstance(packet.payload, ICMP):
    return (packet.src, packet.dst, packet.proto), 3
  elif isinstance(packet.payload, TCP) or isinstance(packet.payload, UDP):
    return (packet.src, packet.dst, packet.proto, packet.payload.sport, packet.payload.dport), 5
  else:
    return None, "Cannot handle protocol {}.".format(packet.proto)  

def is_ip_tuple(tup):
  if not isinstance(tup, tuple):
    return False
  if len(tup)!=3 and len(tup)!=5:
    return False
  # 1st and 2nd fields must be IPv4 addresses
  if not is_ipv4_address(tup[0]) or not is_ipv4_address(tup[1]):
    return False
  # 3rd field must a protocol number i.e. an integer between 0 and 255
  # for the time being, just accept 1 (ICMP), 6 (TCP) and 17 (UDP)
  if tup[2] not in [1,6,17]:
    return False
  # if protocol is ICMP and we get here, it's a valid tuple
  if tup[2]==1 and len(tup)==3:
    return True
  # we get here if protocol is TCP or UDP
  # 4th and 5th fields must be port numbers i.e. integers between 0 and 65535
  if tup[3]<0 or tup[3]>65535 or tup[4]<0 or tup[4]>65535:
    return False
  # if we get here, it's a valid tuple
  return True

class PacketCounter(Counter):
  def update(self, iterable=None, **kwds):
    # # before updating the Counter, check if iterable is a list of valid IP tuples
    # if iterable is not None:
    #   if isinstance(iterable, tuple):
    #     iterable=[iterable]
    #   for elem in iterable:
    #     if not is_ip_tuple(elem):
    #       raise ValueError("{} not recognized as valid IPv4 tuple.".format(elem))
    super().update(iterable, **kwds)

  def __repr__(self):
    if not self:
      return super().__repr__()
    return '\n'.join(map('Tuple %r observed %r time(s)'.__mod__, self.most_common()))


class BroadcastUDPSocket(socket.socket):
  def __init__(self, *args, **kwargs):
    super().__init__(socket.AF_INET, socket.SOCK_DGRAM, *args, **kwargs)
    self.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


class MusicProtocolSignalHandler():
  def __init__(self, phy, tx_socket=None, rx_socket=None, virtual=False):
    self.phy = phy

    if self.phy == "WIRED":
      self.tx_socket = tx_socket
      self.rx_socket = rx_socket
      self.virtual = virtual
      if self.virtual:
        self.virtual_sound_recorder = mpvirtlib.VirtualSoundRecorder()
        self.virtual_sound_recorder.start()

    elif self.phy == "AUDIO":
      self.sound_handler = mpsoundlib.SoundHandler(0, 2)

    elif self.phy == "VIBRATION":
      # TODO
      pass

    else:
      raise Exception("init: unhandled phy {}".format(self.phy))

  def send(self, signal_sequence, dst=None):
    # signal_sequence is a list of Signal objects or a SignalSequence object
    # dst (optional) is an identifier of the destination of the signal.
    ### if phy == WIRED, it is a pair (tuple) of IP address and port
    if self.phy == "WIRED":
      m = MusicProtocol(sigSeq=signal_sequence)
      self.tx_socket.sendto(raw(m), dst)
    elif self.phy == "AUDIO":
      for s in signal_sequence:
        freq = s.signal
        duration = s.duration
        self.sound_handler.send(freq, duration)
    elif self.phy == "VIBRATION":
      # TODO
      pass
      
    else:
      raise Exception("send: unhandled phy {}".format(self.phy))

  def receive(self):
    if self.phy == "WIRED":
      data, addr = self.rx_socket.recvfrom(4096)
      m = MusicProtocol(data)
      ## TODO check if received packet is a well formed MP packet
      if self.virtual:
        for s in m.sigSeq:
          self.virtual_sound_recorder.record(s.signal, s.sigLen)
      return m.sigSeq
    elif self.phy == "AUDIO":
      # TODO make duration sensible
      duration = 5 
      sensed_freqs = self.sound_handler.receive(duration)
      return [Signal(signal=f, duration=duration) for f in sensed_freqs]
    elif self.phy == "VIBRATION":
      # TODO
      pass
    else:
      raise Exception("receive: unhandled phy {}".format(self.phy))

  def quit(self):
    if self.phy == "WIRED" and self.virtual:
      return self.virtual_sound_recorder.stop()
    else:
      return None

if __name__ == "__main__":

    print("\nHere is a sample packet...\n")

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

    m.show2()



