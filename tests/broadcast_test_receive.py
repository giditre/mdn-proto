from musicproto import *
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

s.bind(('192.168.1.255',12345))
m, addr = s.recvfrom(1024)
MusicProtocol(m).show2()

