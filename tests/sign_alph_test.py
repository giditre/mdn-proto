from musicproto import *

sa = SignalAlphabet(Signal(signal=600), Signal(signal=620), Signal(signal=640))
print(str(sa))
print()

for i in range(10):
  print('i={}'.format(i))
  try:
    sseq = sa.encode_binary(i)
    print('Encoded sequence: {}'.format(sseq))
    n = sa.decode_binary(sseq)
    print('Decoded value: {}'.format(n))
  except ValueError as ve:
    print(ve)
  except TypeError as te:
    print(te)

