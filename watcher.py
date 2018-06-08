#!/usr/bin/env python3

#Face Detection/Recognition utilitys
#to install,  run 
#pip3 install face_recognition
#docs for this are at https://github.com/ageitgey/face_recognition


###Database Layout
#people table
#pid	int auto
#name  varchar(50)
#data  blob 

#faces
#id int aut
#pid int 
#data blob




import struct
import face_recognition
import time
import sys
import MySQLdb
from PIL import Image
import numpy as np
import cv2

db=MySQLdb.connect('localhost','root','aq12ws','face2')
curs=db.cursor()

def encodeFrame(frame):
	print(type(frame))
	l=len(frame)
	print(l)
	
	try:
		subjectEncoding = face_recognition.face_encodings(frame)[0]
		return subjectEncoding
	except:
		print("Failed To find faces in frame")
		print(sys.exc_info())
		return None
				
def faceCompare(known,unknown):
	return face_recognition.face_distance([known], unknown)[0]
	
def getPeopleList():
	q="select data,id from people"
	try:
		curs.execute(q,)
		knownFiles=curs.fetchall()
		return knownFiles
	except:
		print("Failed to fetch people list")
		print(sys.exc_info())
		return None
		
						
def mostLikelyPerson(enc):
	peopleList=getPeopleList()
	
	minScore=100
	minID=0
	try:
		for d,i in peopleList:
			score=faceCompare(enc,d)
			if score<minScore:
				minScore=score
				minID=i
		return minID,minScore
	except:
		return None,1

def findFace(i,upSample):
	faces=[]
	#use basic model for first pass
	face_locations = face_recognition.face_locations(i, number_of_times_to_upsample=upSample)
	for face_location in face_locations:
		top, right, bottom, left = face_location
		newImage=i[top:bottom, left:right]
		#should never need to upsample this 
		face_locations_cnn = face_recognition.face_locations(newImage, number_of_times_to_upsample=0, model="cnn")
		if len(face_locations_cnn)==1:
			faces.append(newImage)
	return faces

def addFaceDB(pid,enc):
	#add to face table
	outBA=[]
	for el in enc:
		ba = bytearray(struct.pack("d", el))
		for b in ba:
			outBA.append(b)
	q='insert into faces(pid,data) values(%s,%s)'
	try:
		dat=''.join(map(lambda x: chr(x % 256), outBA))
		curs.execute(q,[str(pid),dat])
		db.commit()
	except:
		db.rollback()
		print("Error Adding faces entry")
		print(sys.exc_info())
	
def addPerson(enc):
	#add new person, return pid
	#add to face table
	outBA=[]
	for el in enc:
		ba = bytearray(struct.pack("d", el))
		for b in ba:
			outBA.append(b)
	q='insert into people(data) values(%s)'
	try:
		dat=''.join(map(lambda x: chr(x % 256), outBA))
		curs.execute(q,[dat])
		db.commit()
	except:
		db.rollback()
		print("Error Adding faces entry")
		print(sys.exc_info())
		return
	q='select pid from people order by pid desc limit 1'
	try:
		curs.execute(q,)
		return curs.fetchone()[0]
	except:
		print("Error getting last pid")
		print(sys.exc_info())
		return None
	

def processFame(frame,show):
	#given a frame from video, check it for faces, if there is any, save to db
	faces=findFace(frame,0)
	print("I found {} face(s) in this frame.".format(len(faces)))
	for face in faces:
		enc=encodeFrame(frame)
		if enc is None:
			return
		pid,score=mostLikelyPerson(enc)
		print("PID:"+str(pid))
		print("Score:"+str(score))
		if score<.6:
			#we know this person, only add to faces
			addFaceDB(pid,enc)
		else:
			#new person
			pid=addPerson(enc)
			if pid is not None:
				addFaceDB(pid,enc)
				pil_image = Image.fromarray(face)
				pil_image.save("/home/chadg/pyFace/newPeople/"+str(pid)+".jpg")			
			

def captureThread():	
	cap = cv2.VideoCapture(0)
	while(True):
		x=input("HitEnter")
		t=time.time()
		# Capture frame-by-frame
		ret, frame = cap.read()

		# Our operations on the frame come here
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		processFame(gray,False)
		# Display the resulting frame
		cv2.imshow('frame',gray)
		if cv2.waitKey(1) & 0xFF == ord('q'):
			break
		fps=int(1/(time.time()-t))
		print("FPS: {}".format(fps))
	# When everything done, release the capture
	cap.release()
	cv2.destroyAllWindows()

if __name__=="__main__":
		captureThread()
	
	
	
