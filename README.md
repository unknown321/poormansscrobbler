#poormansscrobbler
Python-based scrobbler for iPod Nano 7th gen.

#how should it work

Track info is stored in `iPod_Control/iTunes/iTunes Library.itlp/Library.itdb` which is a simple sqlite3 db file. Playcounts are stored in `iPod_Control/iTunes/Play Counts` file, which is binary.

File format:

| Address | stuff |
| --- | --- |
| 0x00000000 - 0x00000090 | header |
| 0x00000090 - end | records |

Record size per track is 40 bytes long. First 4 bytes (or maybe 2?) are the track count, others are irrelevant.

Records are stored according to 'physical_order' value in `Library.itdb/items` table starting with 0, ie song with physical_order 0 will have its playcount at address 0x00000090.

