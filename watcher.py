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



from threading import Thread
from queue import Queue
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
currentPerson=None
currentPersonTime=None
def encodeFrame(frame):
	try:
		subjectEncoding = face_recognition.face_encodings(frame)[0]
		return subjectEncoding
	except:
		#print("Failed To find faces in frame")
		#print(sys.exc_info())
		return None
				
def faceCompare(known,unknown):
	return face_recognition.face_distance([known], unknown)[0]
	
def getPeopleList():
	q="select data,pid,name from people"
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
	if len(peopleList)==0:
		return None,1,""
	for e in peopleList:
		try:
			encodedValue=[]
			for x in range(128):
				tmp=[]
				for y in range(8):
					tmp.append(e[0][(x*8)+y])
				encodedValue.append(struct.unpack('d',bytearray(tmp))[0])
			data=np.array(encodedValue)
		except:
			print("Failed to Data in float list")
			print(sys.exc_info())
			return None,1,""
		score=faceCompare(enc,data)
		if score<minScore:
			minScore=score
			minID=e[1]
			name=e[2]
	return minID,minScore,name

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
	global currentPerson,currentPersonTime
	#given a frame from video, check it for faces, if there is any, save to db
	faces=findFace(frame,0)
	#print("I found {} face(s) in this frame.".format(len(faces)))
	for face in faces:
		enc=encodeFrame(face)
		if enc is None:
			return
		pid,score,name=mostLikelyPerson(enc)
		#print("PID:"+str(pid))
		#print("Score:"+str(score))
		if score<.6:
			
			if currentPerson!=pid:
				currentPerson=pid
				currentPersonTime=time.time()
				if name is not None:
					print("I see: "+name)
				else:
					print("I recognize them, but dont know name: "+str(pid))
			#we know this person, only add to faces
			addFaceDB(pid,enc)
			return pid
		else:
			#new person
			print("I see a new person")
			pid=addPerson(enc)
			if pid is not None:
				addFaceDB(pid,enc)
				pil_image = Image.fromarray(face)
				pil_image.save("/home/chadg/pyFace/newPeople/"+str(pid)+".jpg")
			return None
	return None			

def unpackEnc(d):
	encodedValue=[]
	for x in range(128):
		tmp=[]
		for y in range(8):
			tmp.append(d[(x*8)+y])
			encodedValue.append(struct.unpack('d',bytearray(tmp))[0])
	return np.array(encodedValue)


def dbThread(queue):
	while True:
		print("dbThreadRunning")
		try:
			pid=queue.get(False)
		except:
			print("Nothing in Queue")
			time.sleep(5)
			continue
		print("updating db for pid: "+str(pid))
		q="select data from faces where pid=%s"
		try:
			curs.execute(q,[pid])
			dataSet=curs.fetchall()
		except:
			print("Failed to data from faces")
			print(sys.exc_info())
			continue
		minAveScore=1
		minData=None
		for n in range(len(dataSet)):
			s=unpackEnc(dataSet[n])
			for m in range(len(dataSet)):
				total=0
				cnt=0
				if m==n:
					#dont match with self
					continue
				t=unpackEnc(dataSet[m])
				total=total+faceCompare(s,t)
				cnt=cnt+1
			total=total/cnt
			if total<minAveScore:
				minAveScore=total
				minData=DataSet[n]
		if minData is None:
			print("Didnt find a min??")
			continue
		q='update people set data=%s where pid=%s'
		try:
			curs.execute(q,[minData,str(pid)])
			db.commit()
		except:
			db.rollback()
			print("Error updating people data")
			print(sys.exc_info())
				
					
	#pull all data from faces table with that pid
	#for each point, compare it to all others (except its self) and keep track of the average score
	# the data point with the lowest overall average should be used to update the data point for their entry in people table. 
	

def reQueueAll(queue):
	q="select pid from people"
	try:
		curs.execute(q,)
		pidList=curs.fetchall()
	except:
		print("Failed to get PID list from people")
		print(sys.exc_info())
		return
	for p in pidList:
		queue.put(p)
	

def captureThread(q):
	global currentPerson,currentPersonTime	
	cap = cv2.VideoCapture(0)
	fpsAve=0
	fpsCnt=0
	while(True):
		
		t=time.time()
		if currentPersonTime is not None:
			if time.time()-currentPersonTime>5:
				currentPerson=None
				currentPersonTime=None
		try:
			ret, frame = cap.read()
		except:
			print("im fail")
			continue
		rgb_frame = frame[:, :, ::-1]
		pid=processFame(rgb_frame,False)
		if pid is not None:
			q.put(pid)
		cv2.imshow('frame',frame)
		if cv2.waitKey(1) & 0xFF == ord('q'):
			break
		if fpsCnt>20:
			print("FPS: "+str(int(fpsAve/fpsCnt)))
			fpsCnt=0
			fpsAve=0
		fpsCnt=fpsCnt+1
		fpsAve=fpsAve+(int(1/(time.time()-t)))
	cap.release()
	cv2.destroyAllWindows()

personQueue=Queue()


if __name__=="__main__":
		cT=Thread(target=captureThread,args=(personQueue,))
		dT=Thread(target=dbThread,args=(personQueue,))
		cT.name="captureThread"
		dT.name="dbThread"
		cT.daemon=True
		dT.daemon=True
		cT.start()
		dT.start()
		reQueueAll(personQueue)
		while True:
			print("Main Running")
			time.sleep(5)
			if not cT.isAlive():
				print("Restarting captureThread")
				cT=Thread(target=captureThread,args=(captureQueue,))
				cT.name="captureThread"
				cT.daemon=True
				cT.start()
				
			if not dT.isAlive():
				print("Restarting dbThread")
				dT=Thread(target=dbThread,args=(dbQueue,))	
				dT.name="dbThread"	
				dT.daemon=True
				dT.start()
	
