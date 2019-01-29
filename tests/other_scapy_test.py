from scapy.packet import Packet
from scapy.fields import *

class RepeatingGroupedSequence(Packet):
    name = "Simple group of two fields"

    fields_desc = [IntField('field1', 1), 
                   IntField('field2', 2)]

    def extract_padding(self, s):
        return '', s

class TopLayer(Packet):
    name = "Storage for Repeating Sequence"

    fields_desc = [FieldLenField("length", None, count_of='rep_seq'),
                   PacketListField('rep_seq', None, RepeatingGroupedSequence, 
                                   count_from = lambda pkt: pkt.length),
                  ]

#Now here is the problem that I have with assembling PacketListField: 

#craft TopLayer packet
p = TopLayer()

#add two "repeated sequences"
p.rep_seq = [ RepeatingGroupedSequence(), RepeatingGroupedSequence(), RepeatingGroupedSequence() ]

#both sequences can observed
print("(1)")
p.show()

#but the underlying structure of the repeated sequence is #Raw# at this stage
print("(2)")
p.show2()

#length is 2
print p.rep_seq, 'length:', len(p.rep_seq)

p.rep_seq.append(RepeatingGroupedSequence())
print("(3)")

p.show()
p.show2()
