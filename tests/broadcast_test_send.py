from musicproto import*
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

p = MusicProtocol()

s.sendto(raw(p), ('192.168.1.255',12345))

