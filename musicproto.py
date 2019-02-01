from scapy.all import *
from collections import Counter
from ipaddress import IPv4Address, IPv4Network

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

class MusicProtocol(Packet):
    name = "MusicProtocolPacket"
    fields_desc = [
            ByteEnumField("phy", 0, {0:"UNSPECIFIED", 0xAA:"AUDIO", 1:"WIFI",
                                    2:"BLUETOOTH", 3:"WIRED"}),
            XByteField("version", 0),
            ShortField("len", None),
            ByteField("channel", 0),
            ShortField("members", 1),
            ShortField("tsDur", 1000),
            ByteEnumField("appId", 0, {0:"UNSPECIFIED", 1:"HHD", 2:"PS"}),
            FieldLenField("sigSeqLen", None, count_of='sigSeq'),
            PacketListField('sigSeq', None, Signal, count_from=lambda pkt:pkt.sigSeqLen)
    ]

    def post_build(self, p, pay):
        p += pay
        if self.len is None:
            p = p[:2] + struct.pack("!H", len(p)) + p[4:]
        return p

class SignalSequence(list):
  def __init__(self, *args):
    super().__init__()
    self.extend(args)

  def __str__(self):
    if not self:
      return super().__str__()
    return '; '.join(["{}".format(s) for s in self])

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
    # before updating the Counter, check if iterable is a list of valid IP tuples
    if iterable is not None:
      if isinstance(iterable, tuple):
        iterable=[iterable]
      for elem in iterable:
        if not is_ip_tuple(elem):
          raise ValueError("{} not recognized as valid IPv4 tuple.".format(elem))
    super().update(iterable, **kwds)

  def __repr__(self):
    if not self:
      return super().__repr__()
    return '\n'.join(map('Tuple %r observed %r time(s)'.__mod__, self.most_common()))
      

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
