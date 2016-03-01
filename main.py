#!/usr/bin/python
import os
import time
import struct
import sqlite3
import errno

COUNTS_PATH = 'PlayCounts'
DB_PATH = 'Library.itdb'

def check_path(path):
	return os.path.isfile(path)

def get_counts(path):
	counts = []
	file_size = os.path.getsize(path)
	#first record starts from 96 byte
	with open(path,'r') as f:
		f.seek(60)
		while True:
			b = f.tell()
			d = b+36
			if d+4 > file_size:
				break
			else:
				f.seek(d)
				a = f.read(4)
				i = struct.unpack('<I',a)
				# print f.tell(), repr(a)
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
		c.execute('SELECT artist, title, album FROM item WHERE physical_order == (?)', (str(phys_order),) )
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
	print len(songs), count
	return 0

if __name__ == '__main__':
	main()
