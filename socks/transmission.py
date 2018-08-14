import os
#import json
import socket
import sys
import time
import binascii
import struct

class SocketOverlay(object):
	def __init__(self, socket):
		self.socket = socket
		
	def recv(self):
		li = self.socket.recv(4)
		l = struct.unpack("I", li)[0]
		return self.socket.recv(l)
		
	def send(self, data):
		l = len(data)
		self.socket.send(struct.pack("I", l))
		self.socket.send(data)
		
	def close(self):
		self.socket.close()
		
class Command(object):
	CMD_GET = 1
	CMD_CLEAR = 2
	CMD_SHUTDOWN = 3
	CMD_GET_CLEAR = 4
	CMD_INFO = 5
	CMD_PAUSE = 6
	CMD_RESUME = 7
	
	def __init__(self):
		self.uCommand = 0
		self.uData = None
	
	def serialise(self):
		if self.uData==None:
			return struct.pack("I", self.uCommand)+struct.pack("I", 0)
		else:
			return struct.pack("I", self.uCommand)+struct.pack("I", len(self.uData))+self.uData
	
	@classmethod
	def build(cls, command, data=None):
		c = Command()
		c.uCommand = command
		c.uData = data
		return c
		
	@classmethod
	def unserialise(cls, data):
		cmd = struct.unpack("I", data[:4])[0]
		ds = struct.unpack("I", data[4:8])[0]
		if ds<1:
			return Command.build(cmd)
		else:
			return Command.build(cmd, data[8:8+ds])
		
