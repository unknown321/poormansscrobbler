#!/usr/bin/python
import os
import time
import struct
import sqlite3
import errno

COUNTS_PATH = 'PlayCounts'		# it should be 'Play Counts'
DB_PATH = 'Library.itdb'
LOCAL_DB_PATH = 'db.sqlite3'

class Song(object):
	"""docstring for Song"""
	def __init__(self, _pid, _artist, _album, _title, _playcount):
		super(Song, self).__init__()
		self.pid = _pid
		self.artist = _artist
		self.album = _album
		self.title = _title
		self.playcount = _playcount
		self.hashstring = ""

	def create_hashstring(self):
		# creates a hashed string for last.fm
		return self.hashstring
		

class LocalDB(object):
	"""docstring for LocalDB"""
	def __init__(self, arg):
		super(LocalDB, self).__init__()
		self.arg = arg

	def create():
		if not check_path(LOCAL_DB_PATH):
			conn = sqlite3.connect(LOCAL_DB_PATH)
			c = conn.cursor()
			conn.close()

	def update_song(song):
		# updates a single song
		# songs removed from iPod should remain in database - they still exist in iTunes
		pass

	def add_song(song):
		pass

def check_path(path):
	return os.path.isfile(path)

def get_counts(path):
	counts = []
	file_size = os.path.getsize(path)
	# first record starts from 96 byte
	# 60 + 36 = 96
	# never use tell(), it lies a lot
	# http://stackoverflow.com/questions/19730875/python-file-tell-gives-wrong-value-location
	pos = 60
	with open(path,'r') as f:
		f.seek(pos)
		while True:
			pos = pos+36
			if pos+4 > file_size:
				break
			else:
				f.seek(pos)
				a = f.read(4)
				i = struct.unpack('<I',a)
				pos = pos + 4
				counts.extend(i)
	return counts

def get_selected_songs(_dbpath, _songs_ids):
	# gets songs info with at least one playcount from library
	# there is no point in getting songs with zero playcounts
	conn = sqlite3.connect(_dbpath)
	c = conn.cursor()
	songs = []
	for i in _songs_ids:
		phys_order = i[0]
		play_count = i[1]
		c.execute('SELECT pid, artist, title, album FROM item WHERE physical_order == (?)', (str(phys_order),) )
		songs.append((c.fetchone(), play_count))
	conn.close()
	return songs

def get_songs_ids(_counts):
	# remove zeroes leaving only songs which were played
	ids = []
	for physical_order, playcount in enumerate(_counts):
		if playcount > 0:
			ids.append((physical_order,playcount))
	return ids

def scrobble_bulk():
	# scrobbles 50 tracks per once
	pass

def get_playcounts_diff():
	# creates diff between two playcount files AND LIBRARIES
	# returns changed/added songs with amount of scrobbles
	pass

def main():
	if not (check_path(COUNTS_PATH) and check_path(DB_PATH)):
		raise OSError(os.strerror(errno.ENOENT))
	counts = get_counts(COUNTS_PATH)
	songs_ids = get_songs_ids(counts)
	songs = get_selected_songs(DB_PATH,songs_ids)
	count = 0
	for s in songs:
		print s
		count = count + s[1]
	print len(songs),'songs', count, 'plays'
	return 0

if __name__ == '__main__':
	main()
