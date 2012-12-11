#! /usr/bin/python -u
from collections import namedtuple
import xml.etree.cElementTree as ET
import io,zlib,sys,struct,os
from tempfile import mkdtemp, mkstemp
from subprocess import Popen, PIPE
from io import SEEK_CUR

# .dmg
#OFFSETS = {'dev': 3318272,'examples': 4256256,'doc': 18440704,'runtime': 58556928}
# .img
#OFFSETS = {'dev': 3284992,'examples': 4222976,'doc': 18407424,'runtime': 58523648}

def decode_xar_header(header_bytes):
	header_fmt = '>4sHHQQI'
	XARHeader = namedtuple('XARHeader', 'magic size version toc_length_compressed toc_length_uncompressed chksum_alg')
	header = XARHeader._make(struct.unpack_from(header_fmt, header_bytes))
	if header.magic != 'xar!':
		raise Exception('Wrong magic %s'%header.magic)
	#wo_dmg.seek(xar_offset+header.size)
	return header

def read_xar_from_dmg(wo_dmg, entry):
	xar_offset = OFFSETS[entry]
	wo_dmg.seek(xar_offset)
	header = decode_xar_header(wo_dmg.read(28))

def extract_toc(header, xar):
	toc = zlib.decompress(xar.read(header.toc_length_compressed))
	if header.toc_length_uncompressed != len(toc):
		raise Exception('Wrong toc length')
	return toc

def extract_xar(xar):
	with open(xar, mode='rb') as f:
		try:
			header = decode_xar_header(f.read(28))
			toc = extract_toc(header, f)
			tree = ET.fromstring(toc)
			for e in ET.ElementPath.findall(tree, "toc/file"):
				if e.find('name', '*').text == 'Payload':
					data = e.find('data', '*')
					length = long(data.find('length').text)
					size = long(data.find('size').text)
					payload_offset = long(data.find('offset').text)
			sys.stderr.write('%s: Payload at offset %d, %d (%d) bytes long\n'%(xar, payload_offset, length, size))
			f.seek(payload_offset, SEEK_CUR)
			tempdir = mkdtemp(prefix=os.path.basename(xar))
			p = Popen(['cpio', '-i', '--quiet'], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=tempdir)
			d = zlib.decompressobj(-zlib.MAX_WBITS)
			gzip_header = f.read(10)
			data = f.read(length)
			#t = mkstemp()
			#with open(mkstemp()[1], mode='w') as t:
			#	try:
			#		t.write(data)
			#	finally:
			#		t.close()
			io = p.communicate(input=d.decompress(data))
			#io = p.communicate()
			if io[1] == '':
				print tempdir
			else:
				print "Error: %s"%io[1]
			#print io[0], io[1]
		finally:
			f.close()

def main(argv):
	if argv[1] == '-x':
		extract_xar(argv[2])
	else:
		with io.open(sys.argv[1], mode='rb') as f:
			try:
				if len(argv) > 1:
					offsets = argv[2:]
				else:
					offsets = OFFSETS.keys()
				for e in offsets:
					extract_xar(f, e)
			finally:
				f.close()

sys.exit(main(sys.argv))
