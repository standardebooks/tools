#!/usr/bin/env python3
"""
Defines helper functions for working with mobi files.

Extracted from KindleUnpack code and modified.

https://www.mobileread.com/forums/showpost.php?p=3165291
"""

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
# Copyright (C) 2013 P. Durrant, K. Hendricks, S. Siebert, fandrieu, DiapDealer, nickredding.
from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import os
import getopt
import struct
import locale
import codecs
import traceback

text_type = str
binary_type = bytes

# Because Windows (and Mac OS X) allows full unicode filenames and paths
# any paths in pure bytestring python 2.X code must be utf-8 encoded as they will need to
# be converted on the fly to full unicode for Windows platforms.  Any other 8-bit str
# encoding would lose characters that can not be represented in that encoding

# these are simple support routines to allow use of utf-8 encoded bytestrings as paths in main program
# to be converted on the fly to full unicode as temporary un-named values to prevent
# the potential mixing of unicode and bytestring string values in the main program

fsencoding = sys.getfilesystemencoding()

def pathof(s, enc=fsencoding):
	if s is None:
		return None
	if isinstance(s, text_type):
		return s
	if isinstance(s, binary_type):
		try:
			return s.decode(enc)
		except:
			pass
	return s

class DualMetaFixException(Exception):
	pass

# palm database offset constants
number_of_pdb_records = 76
first_pdb_record = 78

# important rec0 offsets
mobi_header_base = 16
mobi_header_length = 20
mobi_version = 36
title_offset = 84

def getint(data,ofs,sz=b'L'):
	i, = struct.unpack_from(b'>'+sz,data,ofs)
	return i

def writeint(data,ofs,n,len=b'L'):
	if len==b'L':
		return data[:ofs]+struct.pack(b'>L',n)+data[ofs+4:]
	else:
		return data[:ofs]+struct.pack(b'>H',n)+data[ofs+2:]

def getsecaddr(datain,secno):
	nsec = getint(datain,number_of_pdb_records,b'H')
	if (secno < 0) | (secno >= nsec):
		emsg = 'requested section number %d out of range (nsec=%d)' % (secno,nsec)
		raise DualMetaFixException(emsg)
	secstart = getint(datain,first_pdb_record+secno*8)
	if secno == nsec-1:
		secend = len(datain)
	else:
		secend = getint(datain,first_pdb_record+(secno+1)*8)
	return secstart,secend

def readsection(datain,secno):
	secstart, secend = getsecaddr(datain,secno)
	return datain[secstart:secend]

# overwrite section - must be exact same length as original
def replacesection(datain,secno,secdata):
	secstart,secend = getsecaddr(datain,secno)
	seclen = secend - secstart
	if len(secdata) != seclen:
		raise DualMetaFixException('section length change in replacesection')
	datalst = []
	datalst.append(datain[0:secstart])
	datalst.append(secdata)
	datalst.append(datain[secend:])
	dataout = b"".join(datalst)
	return dataout

def get_exth_params(rec0):
	ebase = mobi_header_base + getint(rec0,mobi_header_length)
	if rec0[ebase:ebase+4] != b'EXTH':
		raise DualMetaFixException('EXTH tag not found where expected')
	elen = getint(rec0,ebase+4)
	enum = getint(rec0,ebase+8)
	rlen = len(rec0)
	return ebase,elen,enum,rlen

def add_exth(rec0,exth_num,exth_bytes):
	ebase,elen,enum,rlen = get_exth_params(rec0)
	newrecsize = 8+len(exth_bytes)
	newrec0 = rec0[0:ebase+4]+struct.pack(b'>L',elen+newrecsize)+struct.pack(b'>L',enum+1)+\
			  struct.pack(b'>L',exth_num)+struct.pack(b'>L',newrecsize)+exth_bytes+rec0[ebase+12:]
	newrec0 = writeint(newrec0,title_offset,getint(newrec0,title_offset)+newrecsize)
	# keep constant record length by removing newrecsize null bytes from end
	sectail = newrec0[-newrecsize:]
	if sectail != b'\0'*newrecsize:
		raise DualMetaFixException('add_exth: trimmed non-null bytes at end of section')
	newrec0 = newrec0[0:rlen]
	return newrec0

def read_exth(rec0,exth_num):
	exth_values = []
	ebase,elen,enum,rlen = get_exth_params(rec0)
	ebase = ebase+12
	while enum>0:
		exth_id = getint(rec0,ebase)
		if exth_id == exth_num:
			# We might have multiple exths, so build a list.
			exth_values.append(rec0[ebase+8:ebase+getint(rec0,ebase+4)])
		enum = enum-1
		ebase = ebase+getint(rec0,ebase+4)
	return exth_values

def del_exth(rec0,exth_num):
	ebase,elen,enum,rlen = get_exth_params(rec0)
	ebase_idx = ebase+12
	enum_idx = 0
	while enum_idx < enum:
		exth_id = getint(rec0,ebase_idx)
		exth_size = getint(rec0,ebase_idx+4)
		if exth_id == exth_num:
			newrec0 = rec0
			newrec0 = writeint(newrec0,title_offset,getint(newrec0,title_offset)-exth_size)
			newrec0 = newrec0[:ebase_idx]+newrec0[ebase_idx+exth_size:]
			newrec0 = newrec0[0:ebase+4]+struct.pack(b'>L',elen-exth_size)+struct.pack(b'>L',enum-1)+newrec0[ebase+12:]
			newrec0 = newrec0 + b'\0'*(exth_size)
			if rlen != len(newrec0):
				raise DualMetaFixException('del_exth: incorrect section size change')
			return newrec0
		enum_idx += 1
		ebase_idx = ebase_idx+exth_size
	return rec0

class DualMobiMetaFix:

	def __init__(self, infile, asin):
		self.datain = open(pathof(infile), 'rb').read()
		self.datain_rec0 = readsection(self.datain,0)
		self.asin = asin.encode('utf-8')

		# in the first mobi header
		# add 501 to "EBOK", add 113 as asin, add 504 as asin
		rec0 = self.datain_rec0
		rec0 = del_exth(rec0, 501)
		rec0 = del_exth(rec0, 113)
		rec0 = del_exth(rec0, 504)
		rec0 = add_exth(rec0, 113, self.asin)
		rec0 = add_exth(rec0, 504, self.asin)
		rec0 = add_exth(rec0, 501, b'EBOK')
		self.datain = replacesection(self.datain, 0, rec0)

		ver = getint(self.datain_rec0,mobi_version)

	def getresult(self):
		return self.datain

def update_asin(asin, infile, outfile):
	dmf = DualMobiMetaFix(infile, asin)
	open(pathof(outfile),'wb').write(dmf.getresult())
