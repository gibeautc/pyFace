#!/usr/bin/env python3

#Face Detection/Recognition utilitys
#to install,  run 
#pip3 install face_recognition
#docs for this are at https://github.com/ageitgey/face_recognition


import struct
import face_recognition
from os import walk
import time
import sys
import MySQLdb


db=MySQLdb.connect('localhost','root','aq12ws','faceDB')
curs=db.cursor()


#encodes a picture (hopefully a face picture) and stores it in the database
def encodeFile(filename):
	subject = face_recognition.load_image_file(filename)
	subjectEncoding = face_recognition.face_encodings(subject)[0]
	outBA=[]
	for el in subjectEncoding:
		ba = bytearray(struct.pack("d", el))
		for b in ba:
			outBA.append(b)
	q='insert into faceEncoding(filename,data) values(%s,%s)'
	try:
		curs.execute(q,[filename,str(outBA)])
		dbb.commit()
	except:
		dbb.rollback()
		log.error("Error Adding faceEncoding entry")
		log.error(sys.exc_info())
		


if __name__=="__main__":
	encodeFile("/home/chadg/pyFace/Known/subject01.gif")
