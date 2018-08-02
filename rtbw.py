import sys
import os
import os.path
import traceback
import json
import socket
import time
import datetime
import json
import re
import time
import threading
import binascii
from cffi import FFI
import select
from subprocess import Popen, PIPE
import argparse
try:
    import ssl
except ImportError:
    print ("error: no ssl support")
import requests

def __pmap():
	return [
		("com", "c")
	]

def __encodepost(post):
	pass #TODO: __pmap comp and lzma comp

class StatBuffer:
	SLV_LOW = 0 #Keep everything
	SLV_NOTEXT = 1 #Remove subject & comment
	SLV_NOUI = 2 #Remove all user inputed information (sub, com, filename)
	SLV_HIGH = 0xFF #Keep only post number	

	def __init__():
		pass
	def _encode(post, striplv):
		if(striplv == StatBuffer.SLV_LOW):
			return __encodepost(post)
		elif(striplv == StatBuffer.SLV_NOTEXT):
			if "com" in post:
				del post["com"]
			if "sub" in post:
				del post["sub"]
			return __encodepost(post)
		elif(striplv == StatBuffer.SLV_NOUI):
			if "com" in post:
				del post["com"]
			if "sub" in post:
				del post["sub"]
			#TODO: Remove image stuff
			return __encodepost(post)
		elif(striplv == StatBuffer.SLV_HIGH):
			return post["no"]
		else: return None
	def write():
		raise NotImplementedError("Abstract method not implemented")
	def read():
		raise NotImplementedError("Abstract method not implemented") 

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

def parse_page(api, board, page, last):
	dta = requests.get((api % board)+page+".json")
	posts = list()	
	page = dta.json()
	for thread in page["threads"]:
		post =  thread["posts"][0]
		if post["no"] <= last:
			continue
		else:
			fullThread = requests.get((api % board)+"thread/"+str(post["no"])+".json").json()
			for fPost in fullThread["posts"]:
				np = parse_post(fPost)
				if(np!=None):
					posts.append(np)
				
	return posts

def pnomax(last, posts):
	mx=last
	for post in posts:
		if(post["no"]>mx): mx = post["no"] #we need this because of sage
	return mx

def log(stre):
	print (stre)

def buffer_write(buf, posts):
	#TODO: Write buffer stuff
	pass

parser = argparse.ArgumentParser(description="Real-time 4chan board watcher.")
parser.add_argument("board", help="Board to spider")
parser.add_argument("timeout", help="Time between cycles")
parser.add_argument("--buffer", help="Save buffer filename (default: use in memory buffer)", default=None)
parser.add_argument("--daemon", action="store_true", help="Run as daemon")
parser.add_argument("--api", help="Base URL of 4chan JSON API", default="http://api.4chan.org/%s/")

args = parser.parse_args()
last=0

if args.buffer !=None:
	pass #TODO: Init buffer stuff

while True:
	log("Reading threads for %s from %d" % (args.board, last))
	posts = parse_page(args.api, args.board, "1", last)
	last = pnomax(last, posts)

	if(len(posts)>0):
		log("%d new posts since last cycle" % len(posts))
		buffer_write(posts)
	else:
		log("Nothing new")
	
	time.sleep(int(args.timeout))
