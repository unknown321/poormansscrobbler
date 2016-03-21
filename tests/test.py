import unittest
from  poormansscrobbler.scrobbler import scrobbler
import ConfigParser
PATH = 'poormansscrobbler/tests/testdata/config.cfg'

class MyTest(unittest.TestCase):
	def setUp(self):
		f = open(PATH,'w')
		f.write('[lastfm]\n')
		f.write('username=1\n')
		f.write('password=2')
		f.close()

	def test_reading_lastfm_credentials(self):
		self.assertEqual(scrobbler.get_credentials(PATH), {'username':'1','password':'2'})

if __name__ == '__main__':
	unittest.main()