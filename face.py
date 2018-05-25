#!/usr/bin/env python3

#Face Detection/Recognition utilitys
#to install,  run 
#pip3 install face_recognition
#docs for this are at https://github.com/ageitgey/face_recognition


import struct
import face_recognition
import time
import sys
import MySQLdb
import os
import numpy as np
import random
from PIL import Image

db=MySQLdb.connect('localhost','root','aq12ws','faceDB')
curs=db.cursor()

def findUniqueID(lst):
	if lst is None:
		q="select id from faceEncoding"
		try:
			curs.execute(q,)
			data=curs.fetchall()
		except:
			print("Failed to fetch ID's from faceEncoding")
			print(sys.exc_info())
			return None
	else:
		data=lst
	while True:
		num=random.randint(100,1000)
		unique=True
		for d in data:
			if num==d:
				unique=False
		if unique is True:
			#print("Found Unique ID: "+str(num))
			return num
		

#encodes a picture (hopefully a face picture) and stores it in the database
def encodeFile(filename,known):
	n=0
	if known:
		n=findUniqueID(None)

	try:
		subject = face_recognition.load_image_file(filename)
		subjectEncoding = face_recognition.face_encodings(subject)[0]
	except:
		print("Failed To find faces in file")
		return None
	#print(subjectEncoding)
	outBA=[]
	for el in subjectEncoding:
		ba = bytearray(struct.pack("d", el))
		for b in ba:
			outBA.append(b)
	#print("Length of Data: "+str(len(outBA)))
	#print(outBA)
	q='insert into faceEncoding(filename,data,known,id) values("'+filename+'",%s,'+str(known)+','+str(n)+')'
	try:
		curs.execute(q,[''.join(map(lambda x: chr(x % 256), outBA))])
		db.commit()
	except:
		db.rollback()
		#print("Error Adding faceEncoding entry")
		#print(sys.exc_info())
	return subjectEncoding	
		
def getEncoding(filename):
	q="select data from faceEncoding where filename=%s" 
	try:
		curs.execute(q,[filename,])
		data=curs.fetchone()[0]
		#print(data)
		#print("Lhttp://www.openbookproject.net/books/bpp4awd/ch03.htmlength of Data: "+str(len(data)))
	except:
		print("Failed to fetch encoding from faceEncoding")
		print(sys.exc_info())
		return None
	
	try:
		encodedValue=[]
		for x in range(128):
			tmp=[]
			for y in range(8):
				tmp.append(data[(x*8)+y])
			encodedValue.append(struct.unpack('d',bytearray(tmp))[0])
			
		#print(encodedValue)	
		#print(len(encodedValue))
		return np.array(encodedValue)
	except:
		print("Failed to Data in float list")
		print(sys.exc_info())
		return None
def faceMatch(known,unknown,cutoff):
	result=face_recognition.face_distance([known], unknown)
	if result<cutoff:
		return True
	return False
	
def faceCompare(known,unknown):
	return face_recognition.face_distance([known], unknown)[0]
	
def loadKnownFolder(path):
	files = []
	for (dirpath, dirnames, filenames) in os.walk(path):
		files.extend(filenames)
		break
	for f in files:
		encodeFile(path+f,True)

def loadUnKnownFolder(path):
	files = []
	for (dirpath, dirnames, filenames) in os.walk(path):
		files.extend(filenames)
		break
	for f in files:
		encodeFile(path+f,False)
		print("Loaded: "+f)

def getID(path):
	q="select id from faceEncoding where filename=%s"
	try:
		curs.execute(q,[path,])
		return curs.fetchall()[0]
	except:
		print("Failed to fetch ID from filename from faceEncoding")
		print(sys.exc_info())
		return None

def setID(path,ID):
	print("UPDATING ID")
	print(path)
	print(ID)
	q="update faceEncoding set id=%s where filename=%s"
	try:
		curs.execute(q,[str(ID),path])
		db.commit()
	except:
		db.rollback()
		print("Failed to update ID from filename from faceEncoding")
		print(sys.exc_info())

def getKnownFileList():
	q="select filename,id from faceEncoding where known=1"
	try:
		curs.execute(q,)
		knownFiles=curs.fetchall()
		return knownFiles
	except:
		print("Failed to fetch known filenames from faceEncoding")
		print(sys.exc_info())
		return None
		


def processUnknown(limit):
	q="select filename from faceEncoding where id=0"
	try:
		curs.execute(q,)
		unKnownFiles=curs.fetchall()
	except:
		print("Failed to fetch known filenames from faceEncoding")
		print(sys.exc_info())
		return None
	knownFiles=getKnownFileList()#returns path and ID
	for f in unKnownFiles:
		fID,fScore=mostLikelyPerson(f)
		if fScore<=limit:
			setID(f,fID)
				
def mostLikelyPerson(path):
	enc=getEncoding(path)
	knownFiles=getKnownFileList()
	minScore=100
	minID=0
	for f,i in knownFiles:
		comp=getEncoding(f)
		score=faceCompare(enc,comp)
		if score<minScore:
			minScore=score
			minID=i
	return minID,minScore

def findSaveFacesFromImages(path,show):
	files = []
	for (dirpath, dirnames, filenames) in os.walk(path):
		files.extend(filenames)
		break
	for f in files:	
		#given a folder path, iterate over each picture
		#find any/all faces and save them to a temp directory in that folder
		image = face_recognition.load_image_file(path+f)

		# Find all the faces in the image using a pre-trained convolutional neural network.
		face_locations = face_recognition.face_locations(image, number_of_times_to_upsample=0, model="cnn")

		print("I found {} face(s) in this photograph.".format(len(face_locations)))
		cnt=0
		for face_location in face_locations:
			cnt=cnt+1
			# Print the location of each face in this image
			top, right, bottom, left = face_location
			print("A face is located at pixel location Top: {}, Left: {}, Bottom: {}, Right: {}".format(top, left, bottom, right))
			# You can access the actual face itself like this:
			if show:
				face_image = image[top:bottom, left:right]
				pil_image = Image.fromarray(face_image)
				pil_image.show()
			pil_image=pil_image.convert('L')
			pil_image.save("/home/chadg/pyFace/UnKnown/"+str(cnt)+"_"+f)
		os.rename(path+f,"/home/chadg/pyFace/Processed/"+f)

def resetDB():
	#delete from faceEncoding
	#rescan and ID known folder
	#rescan unknown folder
	#identify knowns
	#check?
	q="delete from faceEncoding"
	try:
		curs.execute(q,)
		db.commit()
	except:
		db.rollback()
		print("Failed to delete all records from faceEncoding")
		print(sys.exc_info())
	print("DB scrubed....")
	loadKnownFolder("/home/chadg/pyFace/Known/")
	print("Known Folder Reloaded")
	matchScore=findMinKnownRelation(None)-.001
	print("Min Score Between Known People(minus .001)")
	print(matchScore)
	loadUnKnownFolder("/home/chadg/pyFace/UnKnown/")
	print("Unknown Folder Reloaded")
	processUnknown(matchScore)
	print("Unknowns Processed")


		
def findMinKnownRelation(specID):
	#spec ID of none is for the whole db, other wise for a specific person
	if specID is None:
		#get all known filenames
		#for each one, compare to all others (ignoring own)
		#keep track of min score
		q="select filename from faceEncoding where known=1"
		try:
			curs.execute(q,)
			data=curs.fetchall()
		except:
			print("Failed to fetch known filenames from faceEncoding")
			print(sys.exc_info())
			return None
		minScores={}
		globalMin=100
		for f in data:
				orig=getEncoding(f)
				minScore=100 #i think the max is only 1... but this is safe
				for m in data:
					if f==m:
						continue
					comp=getEncoding(m)
					score=faceCompare(orig,comp)
					if score<globalMin:
						globalMin=score
					if score<minScore:
						minScore=score
						minScores[f]=minScore
	return globalMin
					

if __name__=="__main__":
	resetDB()
	#matchScore=findMinKnownRelation(None)-.001
	#print("Min Score Between Known People(minus .001)")
	#print(matchScore)
	#processUnknown(matchScore)
	#findSaveFacesFromImages("/home/chadg/pyFace/Other/",True)
	
	
