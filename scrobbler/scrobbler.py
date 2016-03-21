#!/usr/bin/python
import os
import time
import struct
import sqlite3
import errno
import md5
import ConfigParser
import requests
from string import Template
from xml.etree import ElementTree

API_KEY = "f9793a7c8724e215987be37ba5691f62"
SECRET = "3bb8f2f6f2de806b213cb73f53803815"
ROOT_URL ="https://ws.audioscrobbler.com/2.0/"		#You must use HTTPS for this request

COUNTS_PATH = 'PlayCounts'		# it should be 'Play Counts'
DB_PATH = 'Library.itdb'
LOCAL_DB_PATH = 'db.sqlite3'
CONFIG_PATH = 'config.cfg'
# The difference between the Unix timestamp epoch (1970) and the Mac timestamp epoch (1904)
# should be used for proper timestamps if timestamps will be found in library somewhere
#APPLE_TIME = 2082844800 		
# since there are no proper timestamps, we will have to make some ourselves
# first scrobble will start a week ago
TSTAMP = int(time.time()) - 604800
SONG_TEMPLATE = """$title by $artist from $album; $playcount plays"""
# these fieldnames are ignored when generating signature for a song
IGNORED_FIELDNAMES = ['pid','playcount']

def get_credentials(_c_path=CONFIG_PATH):
	config = ConfigParser.RawConfigParser()
	config.read(_c_path)
	u = config.get('lastfm', 'username')
	p = config.get('lastfm', 'password')
	return {'username':u, 'password':p}

def authenticate(username,password):
	api_sig = md5.md5("api_key"+API_KEY
		+"method"+"auth.getMobileSession"
		+"password"+password
		+"username"+username
		+SECRET).hexdigest()
	p = {"method":"auth.getMobileSession",
		 "api_key":API_KEY,
		 "username": username,
		 "password":password,
		 "api_sig":api_sig}
	t = requests.post(ROOT_URL, params=p)
	tree = ElementTree.fromstring(t.text)
	key = tree.findall('session/key')
	if key:
		key = key[0].text
	return key

class LonelyException(Exception):
	'''Raise when credentials are empty'''
 	pass

class Song(object):
	"""docstring for Song"""
	def __init__(self, _pid, _artist, _album, _title, _playcount, _timestamp=0):
		super(Song, self).__init__()
		self.api_sig = None
		self.method = None
		self.api_key = API_KEY
		self.pid = _pid
		self.artist = _artist
		self.album = _album
		self.track = _title 			# track title is 'track' for lastfm
		self.playcount = _playcount 	# playcount should indicate how many times song should be scrobbled
										# probably with a new timestamp
		self.timestamp = _timestamp 	# timestamps are handled by Bunch class
		self.sk = SESSION_KEY
		self.generate_signature()

	def generate_signature(self, _method='track.scrobble'):
		# artist[i] (Required) : The artist name.
		# track[i] (Required) : The track name.
		# timestamp[i] (Required) : The time the track started playing,
		# api_key (Required) : A Last.fm API key.
		# api_sig (Required) : A Last.fm method signature. See authentication for more information.
		# sk (Required) : A session key generated by authenticating a user via the authentication protocol. 
		if not self.timestamp:
			return 0
		sig_string = u""
		self.api_sig = None
		self.method = _method
		self.timestamp = str(self.timestamp)
		for key, value in sorted(self.__dict__.items()):
			if key not in IGNORED_FIELDNAMES:
				if value:
					sig_string = sig_string + key + value
		self.method = None
		self.timestamp = int(self.timestamp)
		self.api_sig = md5.md5((sig_string+SECRET).encode('utf-8')).hexdigest()
		return 0

	def scrobble(self, method='track.scrobble'):
		self.method = 'track.scrobble'
		p = {}
		p['api_key'] = API_KEY
		for key, value in self.__dict__.items():
			if value:
				p[key] = value
		response = requests.post(ROOT_URL, params=p)
		self.method = None
		return response

	def __str__(self):
		text_template = Template(SONG_TEMPLATE)
		text = text_template.substitute({"artist":self.artist, "title":self.track, 
										 "album":self.album, "playcount":self.playcount})
		return text


class Bunch(object):
	"""a bunch of songs, 50 max"""
	def __init__(self, songs, start_timestamp):
		self.__songs__ = songs
		for s in self.__songs__:
			s.timestamp = start_timestamp
			start_timestamp+=1
		self.__generate_signature__()

	def __len__(self):
		return len(self.__songs__)

	def __generate_signature__(self):
		query_string = u""
		p = {}
		p['method'] = u'track.scrobble'
		p['api_key'] = API_KEY
		p['sk'] = SESSION_KEY
		for s in self.__songs__:
			i = str(self.__songs__.index(s))
			p['artist[{}]'.format(i)] = s.artist
			p['track[{}]'.format(i)] = s.track
			p['timestamp[{}]'.format(i)] = str(s.timestamp)
			if s.album:
				p['album[{}]'.format(i)] = s.album
		for key, value in sorted(p.items()):
			query_string = query_string + key + value
		query_string = query_string + SECRET
		p['api_sig'] = u""
		p['api_sig'] = md5.md5((query_string).encode('utf-8')).hexdigest()
		p['query_string'] = query_string
		self.params = p

	def scrobble(self):
		del self.params['query_string']
		response = requests.post(ROOT_URL, params=self.params)
		self.method = None
		return response


class LocalDB(object):
	"""docstring for LocalDB"""
	def __init__(self):
		super(LocalDB, self).__init__()
		if check_path(LOCAL_DB_PATH):
			pass
		else:
			print 'No local database found, creating a new one'
			self.__create__()
		self.connection = sqlite3.connect(LOCAL_DB_PATH)

	def __create__(self):
		if not check_path(LOCAL_DB_PATH):
			if check_path(DB_PATH):
				conn = sqlite3.connect(LOCAL_DB_PATH)
				c = conn.cursor()
				c.execute('CREATE TABLE item ("pid","artist","album","title","playcount")')
				c.execute('CREATE TABLE new_item ("pid","playcount")')
				self.__populate__(conn)
				conn.close()
			else:
				print 'No iPod database found (Library.itdb), cannot create local database'

	def __populate__(self, _connection):
		'''used only during creation of database
			adds info about songs with playcounts'''
		conn = sqlite3.connect(DB_PATH)
		c = conn.cursor()
		c.execute('SELECT pid, artist, album, title FROM item ORDER BY physical_order')
		songs = c.fetchall()
		conn.close()
		# add playcounts to songs
		if check_path(COUNTS_PATH):
			counts = get_counts(COUNTS_PATH)
			songs_with_playcounts = []
			for n,song in enumerate(songs):
				song = song + (counts[n],)
				songs_with_playcounts.append(song)
			# this is a connection to a local database from __connect__ function
			# feels like I am doing something wrong
			# anyway, don't close this connection yet
			cursor = _connection.cursor()
			cursor.executemany('INSERT INTO item VALUES (?,?,?,?,?)', songs_with_playcounts)
			_connection.commit()
			print 'Added {} songs'.format(str(len(songs)))
		else:
			# actually we can, but I am too lazy to rewrite it
			print 'No Play Counts file found, songs, cannot create local database'
			os.remove(LOCAL_DB_PATH)

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

def get_songs_ids(_counts):
	# remove zeroes leaving only songs which were played
	ids = []
	for physical_order, playcount in enumerate(_counts):
		if playcount > 0:
			ids.append((physical_order,playcount))
	return ids

def get_selected_songs(_dbpath, _songs_ids):
	# gets songs info with at least one playcount from library
	# there is no point in getting songs with zero playcounts
	conn = sqlite3.connect(_dbpath)
	c = conn.cursor()
	songs = []
	for n,i in enumerate(_songs_ids):
		phys_order = i[0]
		play_count = i[1]
		c.execute('SELECT pid, artist, album, title FROM item WHERE physical_order == (?)', (str(phys_order),) )
		r = c.fetchone()
		if play_count > 1:
			for i in range (1,play_count+1):
				s = Song(r[0], r[1], r[2], r[3], i)
				songs.append(s)
		else:
			s = Song(r[0], r[1], r[2], r[3], i)
			songs.append(s)
	conn.close()
	return songs

def get_songs_with_scrobbles():
	# gets songs info from iPod db if its playcount > 1
	songs_to_scrobble = []
	conn_new = sqlite3.connect(DB_PATH)
	c_new = conn_new.cursor()
	c_new.execute('SELECT pid FROM item ORDER BY physical_order')
	new_library_songs = c_new.fetchall()
	counts = get_counts(COUNTS_PATH)
	counts[1] = 1
	songs_from_new_lib_with_playcounts = []
	for n,song in enumerate(new_library_songs):
		if counts[n] > 0:
			song = song + (counts[n],)
			songs_from_new_lib_with_playcounts.append(song)
	conn_new.close()
	return songs_from_new_lib_with_playcounts

def process_new_songs(_added_songs):
	# add new songs __with_playcounts__ to local library, create Song objects from them
	conn_new = sqlite3.connect(DB_PATH)
	c_new = conn_new.cursor()
	conn_local = sqlite3.connect(LOCAL_DB_PATH)
	c_local = conn_local.cursor()
	songs_to_scrobble = []
	# SQLite can't (by default) handle more than 999 parameters to a query
	# there is no nice way to handle this
	for p in _added_songs:
		# get all song info from ipod database, add playcounts, save into localdb
		c_new.execute('SELECT pid, artist, album, title FROM item where pid = ?',(p[0],))
		new_song = c_new.fetchone()
		new_song = new_song + (p[1],)
		c_local.execute('insert into item values (?,?,?,?,?)', new_song )
		conn_local.commit()
		# duplicate songs as many times as it was played
		for i in range (1, new_song[4]+1):
			s = Song(new_song[0], new_song[1], new_song[2], new_song[3], i)
			songs_to_scrobble.append(s)
	conn_new.close()
	conn_local.close()
	return songs_to_scrobble

def find_and_save_chaged_songs():
	# save changed/added songs into temp table to find differences using sql
	songs_from_new_lib_with_playcounts = get_songs_with_scrobbles()
	conn_local = sqlite3.connect(LOCAL_DB_PATH)
	c_local = conn_local.cursor()
	c_local.execute('delete from new_item')
	conn_local.commit()
	c_local.executemany('insert into new_item values (?,?)', songs_from_new_lib_with_playcounts)
	conn_local.commit()
	conn_local.close()


def diff_new_songs():
	# find new songs that were added to iPod judging only by pids
	# we cannot get pid-playcount pairs immidiately because:
	## SELECTs to the left and right of EXCEPT do not have the same number of result columns
	songs_to_scrobble = []
	added_songs = []
	conn_local = sqlite3.connect(LOCAL_DB_PATH)
	c_local = conn_local.cursor()
	c_local.execute('select pid from new_item except select pid from item')
	a_pids = c_local.fetchall()
	for i in a_pids:
		c_local.execute('select pid, playcount from new_item where pid == (?)',(i[0],))
		added_songs.append(c_local.fetchall()[0])
	if added_songs:
		songs_to_scrobble.extend(process_new_songs(added_songs))

	conn_local.commit()
	conn_local.close()
	return songs_to_scrobble

def diff_old_songs():
	# find songs that exist in local database and were played on iPod, create Song objects from them
	songs_to_scrobble = []
	conn_local = sqlite3.connect(LOCAL_DB_PATH)
	c_local = conn_local.cursor()
	c_local.execute('select pid, playcount from new_item except select pid, playcount from item')
	changed_pids = c_local.fetchall()
	if changed_pids:
		# update local db
		# SQLite can't (by default) handle more than 999 parameters to a query
		# there is no nice way to handle this
		for p in changed_pids:
			c_local.execute('SELECT pid, artist, album, title, playcount FROM item WHERE pid == (?)', (p[0], ) )
			r = c_local.fetchone()
			c_local.execute('update item set playcount = (?) where pid = (?)',(p[1], p[0]))
			conn_local.commit()
			for i in range (r[4], p[1]):
				s = Song(r[0], r[1], r[2], r[3], p[1]-i)
				songs_to_scrobble.append(s)

	conn_local.commit()
	conn_local.close()
	return songs_to_scrobble

def clean_temp_table():
	conn_local = sqlite3.connect(LOCAL_DB_PATH)
	c_local = conn_local.cursor()
	c_local.execute('delete from new_item')
	conn_local.commit()
	conn_local.close()

def get_playcounts_diff():
	# returns changed/added songs with amount of scrobbles
	songs_to_scrobble = []
	find_and_save_chaged_songs()
	songs_to_scrobble.extend(diff_new_songs())
	songs_to_scrobble.extend(diff_old_songs())
	clean_temp_table()
	return songs_to_scrobble

def purge_local_db():
	conn_local = sqlite3.connect(LOCAL_DB_PATH)
	c_local = conn_local.cursor()
	c_local.execute('delete from item')
	conn_local.commit()
	conn_local.close()

def ask_about_syncronization():
	# does local database still matter?
	answer = raw_input('First time scrobbling after iTunes sync? [Yes/No]')
	if answer in ['y','Y','Yes', 'YES', 'ye','yes']:
		# this is the first time, all playcounts from local database doesn't matter
		# since playcounts on iPod were set to 0 when it was synced
		# purge local database
		purge_local_db()
		return 0
	elif answer in ['n','N','No','NO','no']:
		# do nothing
		return 0
	else:
		print 'No answer :V'
		return 1


def scrobble_everything(_songs):
	# scrobbles 50 tracks per page
	page = 0
	for i in _songs:
		print unicode(i)
	if len(_songs) > 0:
		while page < (len(_songs)/50 + 1):
			b = Bunch(_songs[page*50:((page+1)*50)-1], TSTAMP)
			resp = b.scrobble()
			if resp.ok:
				tree = ElementTree.fromstring((resp.text).encode('utf-8'))
				status_element = tree.findall('scrobbles')[0]
				status = status_element.attrib
				print "{} tracks scrobbled".format(status['accepted'])
				if len(b) != int(status['accepted']):
					print 'ERROR, page {}, sent {}, accepted {}'.format(page, len(b), status['accepted'])
					return resp.text
				else:
					#print '50 tracks uploaded'
					time.sleep(1)
				page = page+1
	else:
		return 'Nothing to scrobble'
	return 0

def main():
	if not (check_path(COUNTS_PATH) and check_path(DB_PATH)
		and check_path(CONFIG_PATH)):
		raise OSError(os.strerror(errno.ENOENT))
	creds = get_credentials()
	global SESSION_KEY
	SESSION_KEY = authenticate(creds['username'], creds['password'])
	if not SESSION_KEY:
		raise LonelyException("Empty SESSION_KEY, check your credentials")

	if not ask_about_syncronization():
		s = get_playcounts_diff()
		answer = raw_input('Scrobble {} tracks? [Yes/No]'.format(str(len(s))))
		if answer in ['y','Y','Yes', 'YES', 'ye','yes']:
			status = scrobble_everything(s)
			if status is not 0:
				print status
		else:
			# songs were added to local database, but not uploaded
			# this is not good at all, changes should be reverted, but I am lazy
			pass
	return 0

if __name__ == '__main__':
	main()