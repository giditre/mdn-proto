from scapy.all import *


class Signal(Packet):
    name = "SignalPacket"
    
    fields_desc = [
            FlagsField("sigFlag", 0, 1, ["more"]),
            ConditionalField(BitField("padding", 0, 7), lambda pkt:pkt.sigFlag.more==False),
            ConditionalField(BitField("signal", 440, 15), lambda pkt:pkt.sigFlag.more),
            ConditionalField(ShortField("sigLen", 1000), lambda pkt:pkt.sigFlag.more)
    ]

    def extract_padding(self, s):
        return '', s


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
            ByteEnumField("appId", 0, {0:"HDD", 1:"PS"}),
            PacketListField("sigSeq", None, Signal)
    ]

    def post_build(self, p, pay):
        p += pay
        if self.len is None:
            p = p[:2] + struct.pack("!H", len(p)) + p[4:]
        return p


if __name__ == "__main__":

    m = MusicProtocol(
                    phy = 0xAA,
                    version = 0x10,
                    channel = 6,
                    members = 3,
                    tsDur = 300,
                    appId = 0
    )
    
    m.show2()

    signal_length = int(m.tsDur/m.members)

    m.sigSeq = [
            Signal(sigFlag=1, signal=440, sigLen = signal_length),
            Signal(sigFlag=1, signal=460, sigLen = signal_length),
            Signal(sigFlag=1, signal=480, sigLen = signal_length),
            Signal()
    ]

    m.show2()

    # m.sigSeq = [
    #           Signal(sigFlag=0x1, signal=440, sigLen = signal_length),
    #           Signal(sigFlag=0x1, signal=460, sigLen = signal_length),
    #           Signal(sigFlag=0x1, signal=480, sigLen = signal_length),
    #           Signal(sigFlag=0x1, signal=500, sigLen = signal_length),
    #           Signal(sigFlag=0x1, signal=520, sigLen = signal_length),
    #           Signal(sigFlag=0x1, signal=540, sigLen = signal_length)
    # ]

    # m.show2()
    # 
    # m.sigSeq.append(Signal(signal=560, sigLen = signal_length))

    # m.show2()

    send(IP(dst='127.0.0.1')/UDP(sport=12123, dport=18765)/m)

