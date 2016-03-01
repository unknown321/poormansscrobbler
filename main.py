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
				print pos, repr(a)
				# time.sleep(2)
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
