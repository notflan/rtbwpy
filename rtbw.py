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

try:
    import ssl
except ImportError:
    print ("error: no ssl support")
import requests

DEBUG=False

ShowLog=True

def __pmap():
	return {
		"com": "c",
		"thread": "t",
		"no": "n",
		"sub": "s",
		"time": "T",
		"name": "N",
		"trip": "f",
		"country": "C",
		"id": "i",
		"filename": "F",
		"image": "I",
		"realFilename": "l",
		"fileSize": "S"
	}


def log(stre):
	if(ShowLog):
		print (stre)

def encode_post(post):
	mape = __pmap()
	np = dict()
	for k,v in post.items():
		nk = k
		if(k in mape):
			nk = mape[k]
		np[nk] = v
	js = json.dumps(np)
	data = pylzma.compress(js)
	#log("Encoded post from %d to %d bytes (%.2f%% reduction)" % (len(js), len(data), 100.00-(len(data)/len(js))*100.00))
	return data

def decode_post(data):
	js = pylzma.decompress(data).decode("utf-8")
	np = json.loads(js)
	mape = dict((v,k) for k,v in __pmap().items())
	post = dict()
	for k,v in np.items():
		nk = k
		if(k in mape):
			nk = mape[k]
		post[nk] = v
	return post
class StatBuffer:
	SLV_LOW = 0 #Keep everything
	SLV_NOTEXT = 1 #Remove subject & comment
	SLV_NOPI = 2 #Remove all poster information (sub,com,name,trip)
	SLV_NOUI = 3 #Remove all user inputed information (sub, com,name,trip, file info)
	SLV_HIGH = 0xFF #Keep only post number	
	
	def __init__(self):
		self._mutex = Lock()
	def _lock(self):
		self._mutex.acquire()
	def _unlock(self):
		self._mutex.release()
	def _decode(self, data):
		if(isinstance(data, int)):
			return data
		else:
			return decode_post(data)
	def _strip(self, post, string):
		if string in post:
			del post[string]
			post["has_"+string] = True
	def _encode(self, post, striplv):
		if(striplv == StatBuffer.SLV_LOW):
			return encode_post(post)
		elif(striplv == StatBuffer.SLV_NOTEXT):
			self._strip(post, "com")
			self._strip(post, "sub")
			return encode_post(post)
		elif(striplv == StatBuffer.SLV_NOPI):
			self._strip(post, "com")
			self._strip(post, "sub")
			self._strip(post, "name")
			self._strip(post, "trip")
			return encode_post(post)
		elif(striplv == StatBuffer.SLV_NOUI):
			self._strip(post, "com")
			self._strip(post, "sub")
			self._strip(post, "name")
			self._strip(post, "trip")
			return encode_post(post)
			if "filename" in post:
				self._strip(post, "filename")
				del post["fileSize"]
				del post["realFilename"]
				del post["image"]
			return encode_post(post)
		elif(striplv == StatBuffer.SLV_HIGH):
			return encode_post({"no": post["no"]})
		else: return None
	def write(self, post):
		raise NotImplementedError("Abstract method not implemented")
	def read(self):
		raise NotImplementedError("Abstract method not implemented") 
	def close(self): pass

class MemoryBuffer(StatBuffer):
	def __init__(self, level):
		super().__init__()
		self.lvl = level
		self.store = list()
	def write(self, post):
		super()._lock()
		data = super()._encode(post, self.lvl)
		self.store.append(data)
		super()._unlock()
	def raw(self):
		super()._lock()
		try:
			return json.dumps(self.store)
		finally:
			super()._unlock()
	def clear(self):
		super()._lock()
		self.store = list()
		super()._unlock()
	def length(self):
		super()._lock()
		try:
			return len(self.store)
		finally:
			super()._unlock()
	def read(self):
		super()._lock()
		try:
			base = super()
			return list(base._decode(d) for d in self.store)
		finally:
			super()._unlock()
	def findMax(self):
		super()._lock()
		try:
			if len(self.store)<1: return 0
			return super()._decode(self.store[-1])["no"]
		finally:
			super()._unlock()
	def readno(self, floor, ca=False):
		super()._lock()
		posts = list()
		nl = len(self.store)-1
		while(nl>=0):
			entry = super()._decode(self.store[nl])
			if(entry["no"]<=floor): break
			posts.append(entry)
			nl-=1
		if ca:
			self.store = list()
		super()._unlock()
		return posts

class FileBuffer(StatBuffer):
	def __init__(self, fn, level):
		super().__init__()
		self.lvl = level
		self.file = open(fn, "a+b")
	def write(self, post):
		super()._lock()
		data = super()._encode(post, self.lvl)
		self.file.write(data)
		self.file.write(struct.pack("I", len(data)))
		super()._unlock()
	def _readentry(self):
		self.file.seek(-4,1)
		lentr = self.file.read(4)
		if len(lentr)<4: return None
		tl = struct.unpack("I", lentr)[0]
		self.file.seek(-(tl+4), 1)
		ret = super()._decode(self.file.read(tl))
		self.file.seek(-tl,1)
		return ret
	def _skipentry(self):
		self.file.seek(-4,1)
		lentr = self.file.read(4)
		if len(lentr)<4: return False
		tl = struct.unpack("I", lentr)[0]
		self.file.seek(-(tl+4),1)
		return True
	def read(self):
		super()._lock()
		posts = list()
		ent = self._skipentry()
		while self.file.tell()>0 and ent!=None:
			posts.append(ent)
			ent = self._readentry()
		self.file.seek(0,2)
		super()._unlock()
		return posts
	def length(self):
		super()._lock()
		ent = self._skipentry()
		maxl =0
		while self.file.tell()>0 and ent:
			maxl+=1
			ent = self._skipentry()
		self.file.seek(0,2)
		super()._unlock()
		return maxl
	def close(self):
		super()._lock()
		self.file.close()
		super()._unlock()
	def clear(self):
		super()._lock()
		self.file.truncate(0)
		super()._unlock()
	def findMax(self):
		super()._lock()
		try:
			if(self.file.tell()<1): return 0
			sk =  self._readentry()
			self.file.seek(0,2)
			if sk!=None: return sk["no"]
			else: return 0
		finally:
			super()._unlock()
	def readno(self, floor, ca=False):
		super()._lock()
		posts = list()
		if self.file.tell()>0:
			ent = self._readentry()
			while self.file.tell()>0 and ent!=None:
				if(ent["no"]<=floor): break
				posts.append(ent)
				ent = self._readentry()
			self.file.seek(0,2)
		if ca:
			self.file.truncate(0)
		super()._unlock()
		return posts

def parse_post(post):
	res = dict()
	if(not "resto" in post or post["resto"] == 0): #is thread OP
		if("sticky" in post):
			return None
	else:
		res["thread"] = post["resto"]
	res["no"] = post["no"]	
	if("com" in post):
		res["com"] = post["com"]
	if("sub" in post):
		res["sub"] = post["sub"]
	res["time"] = post["now"]

	if("name" in post and post["name"] != "Anonymous"):
		res["name"] = post["name"]
	if("trip" in post):
		res["trip"] = post["trip"]

	if("country" in post):
		res["country"] = post["country"]

	if "id" in post:
		res["id"] = post["id"]	

	if "filename" in post:
		res["filename"] = post["filename"] + post["ext"]
		res["image"] = post["md5"]
		res["realFilename"] = post["tim"]
		res["fileSize"] = post["fsize"]
	
	return res

def parse_thread(api, board, post, last):
	fullThread = requests.get((api % board)+"thread/"+str(post["no"])+".json").json()
	posts = list()
	for fPost in fullThread["posts"]:
		if(fPost["no"] > last):
			np = parse_post(fPost)
			if(np!=None):
				posts.append(np)
	return posts
#if we spider all pages, go from page 10 to 1
def parse_page(api, board, page, last):
	dta = requests.get((api % board)+page+".json")
	posts = list()	
	page = dta.json()
	tpd=0
	for thread in page["threads"]:
		post =  thread["posts"][0]
		if post["no"] <= last:
			#thread is not new
			#are there any new posts?
			for vp in thread["posts"]:
				if(vp["no"] >last):
					posts.extend(parse_thread(api,board,post,last))
					tpd+=1
					break
		else:
			posts.extend(parse_thread(api,board, post,last))
			tpd+=1
	log("\t(threads parsed this rotation: %d)"%tpd)
	return posts

def pnomax(last, posts):
	mx=last
	for post in posts:
		if(post["no"]>mx): mx = post["no"] #we need this because of sage
	return mx


def buffer_write(buf, posts):
	for post in posts:
		buf.write(post)
def _fork():
	if DEBUG:
		return 0
	else:
		return os.fork()

class Daemon(threading.Thread):
	def __init__(self, socket, buf):
		self.sock = socket
		self.buf = buf
		self.running=True
		threading.Thread.__init__(self)
	def _get(self,con, fr, ca=False):
		if ca:
			log("[daemon]: Recieved get-clear from "+str(fr))
		else:
			log("[daemon]: Recieved get from "+str(fr))
		data = self.buf.readno(fr, ca)
		js = json.dumps(data)
		con.send(js.encode("utf-8"))
	def run(self):
		while self.running:
			try:
				con = SocketOverlay(self.sock.accept()[0])
				if not self.running:
					con.close()
					break
				log("[daemon]: Connection accepted")
				read = con.recv()
				cmd = Command.unserialise(read)
				
				if cmd.uCommand == Command.CMD_SHUTDOWN: #shut down daemon
					log("[daemon]: Recieved shutdown")
					self.running=False
				elif cmd.uCommand == Command.CMD_GET: #receive entries from <data>
					self._get(con, struct.unpack("L", cmd.uData)[0])
				elif cmd.uCommand == Command.CMD_GET_CLEAR: #receive entries from <data> then clear
					self._get(con, struct.unpack("L", cmd.uData)[0], True)
				elif cmd.uCommand == Command.CMD_CLEAR: #clear buffer
					log("[daemon]: Recieved clear")
					self.buf.clear()
				else: #unknwon command
					log("[daemon]: Recieved unknown command")
					pass
				con.close()
			except socket.timeout:
				pass
			except:
				self.running=False
				raise
		log("[daemon]: Exiting")
		self.sock.close()
		self.sock=None
	def close(self):
		log("[daemon-ctl]: Shutting down")
		self.running=False

#TODO: When we request buffer data from daemon, send a min post number to send back (last)
parser = argparse.ArgumentParser(description="Real-time 4chan board watcher.")
parser.add_argument("board", help="Board to spider")
parser.add_argument("timeout", help="Time between cycles")
parser.add_argument("--buffer", help="Save buffer filename (default: use in memory buffer)", default=None)
parser.add_argument("--daemon", metavar="Socket", help="Run as daemon", default=None)
parser.add_argument("--api", help="Base URL of 4chan JSON API", default="http://api.4chan.org/%s/")
parser.add_argument("--debug", default=False, action="store_true")

args = parser.parse_args()

DEBUG = args.debug

StripLevel = StatBuffer.SLV_NOTEXT

last=0
buf = None

if args.buffer !=None:
	buf = FileBuffer(args.buffer, StripLevel)
else:
	buf = MemoryBuffer(StripLevel)

last = buf.findMax()

runForever=True
daemon = None

if args.daemon!=None:
	pid = _fork()
	if not pid == 0:
		log("Process forked to background: PID %d" % pid)
		sys.exit(0)
	else:
		runForever=False
		if not DEBUG:
			ShowLog=False
		daemon_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		daemon_sock.bind(args.daemon)
		daemon_sock.settimeout(5)
		daemon_sock.listen(5)
		
		daemon = Daemon(daemon_sock, buf)
		daemon.start()

try:
	while runForever or daemon.running:
		log("Reading threads for %s from %d" % (args.board, last))
		posts = parse_page(args.api, args.board, "1", last)
		last = pnomax(last, posts)

		if(len(posts)>0):
			log("\t%d new posts since last cycle" % len(posts))
			buffer_write(buf, posts)
		else:
			log("\tnothing new")
		log("Buffer written successfully")
		
		time.sleep(int(args.timeout))
except(KeyboardInterrupt):
	log("Interrupt detected")
	if daemon!=None:
		daemon.close()
	buf.close()
log("Closing")
