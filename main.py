#!/usr/bin/python
import os, time, struct
counts = []
size = os.path.getsize('PlayCounts')
print size
#first record is on 96
with open('PlayCounts','r') as f:
	f.seek(60)
	while True:
		b = f.tell()
		d = b+36
		if d+4 > size:
			break
		else:
			f.seek(d)

			a = f.read(4)
			i = struct.unpack('<I',a)
			print f.tell(), repr(a)
			counts.extend(i)
print counts, len(counts)

