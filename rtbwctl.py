import sys
import os
import os.path
import traceback
import json
import socket
import struct
import pprint
import time
import datetime
import threading
import json
import re
import time
from threading import Thread, Lock
import binascii
import pylzma
import select
from subprocess import Popen, PIPE
import argparse

from socks.transmission import SocketOverlay
from socks.transmission import Command

def parsecmd(s):
	if s=="get": return Command.CMD_GET
	elif s=="stop": return Command.CMD_SHUTDOWN
	elif s=="clear": return Command.CMD_CLEAR
	elif s=="get-clear": return Command.CMD_GET_CLEAR
	elif s=="info": return Command.CMD_INFO
	else: return None

parser = argparse.ArgumentParser(description="rtbwpy daemon control.")
parser.add_argument("sock", help="AF_UNIX socket")
parser.add_argument("command", help="Command")
parser.add_argument("--data", help="Additional data to send", default=None)

args = parser.parse_args()

cmd = parsecmd(args.command)

if cmd==None:
	print("Invalid command.")
	os._exit(1)
	
data = args.data

if cmd == Command.CMD_GET or cmd == Command.CMD_GET_CLEAR:
	if data== None:
		data = struct.pack("L", 0)
	else:
		data = struct.pack("L", int(data))

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(args.sock)

con = SocketOverlay(sock)

cmd = Command.build(cmd, data)

con.send(cmd.serialise())

if cmd.uCommand == Command.CMD_GET or cmd.uCommand == Command.CMD_GET_CLEAR:
	json = con.recv().decode("utf-8")
	print(json)

elif cmd.uCommand == Command.CMD_INFO:
	print(con.recv().decode("ascii"))

sock.close()

