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
import shutil
import signal
 
def sigint_handler(signum, frame):
    print('Exiting')
    exit()
 
signal.signal(signal.SIGINT, sigint_handler)



db=MySQLdb.connect('localhost','root','aq12ws','faceDB')
curs=db.cursor()

knownJit=1
unknownJit=1
maxJit=100

def getMinJit():
		q="select jitter from faceEncoding order by jitter limit 1"
		try:
			curs.execute(q,)
			return curs.fetchone()[0]
		except:
			print("Error getting min jitter value")
			print(sys.exc_info())
			return -1
			
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
def encodeFile(filename,known,jit):
	###
	#face_recognition.api.face_encodings(face_image,known_face_locations=None,num_jitters=1)
	#Given an image, return the 128-dimension face encoding for each face in the image.
	#Parameters
	#• face_image– The image that contains one or more faces
	#• known_face_locations – Optional - the bounding boxes of each face if you already know them.
	#• num_jitters –  How  many  times  to  re-sample  the  face  when  calculating  encoding. Higher is more accurate, but slower (i.e. 100 is 100x slower)
	#Returns
	#A list of 128-dimensional face encodings (one for each face in the image)
	###
	
	
	n=0
	if known:
		n=findUniqueID(None)

	try:
		subject = face_recognition.load_image_file(filename)
		subjectEncoding = face_recognition.face_encodings(subject,num_jitters=jit)[0]
	except:
		print("Failed To find faces in file")
		print(sys.exc_info())
		return None
	#print(subjectEncoding)
	outBA=[]
	for el in subjectEncoding:
		ba = bytearray(struct.pack("d", el))
		for b in ba:
			outBA.append(b)
	#print("Length of Data: "+str(len(outBA)))
	#print(outBA)
	q='insert into faceEncoding(filename,data,known,id,jitter) values("'+filename+'",%s,'+str(known)+','+str(n)+','+str(jit)+') on duplicate key update data=%s, jitter=%s'
	#print("Q:"),
	#print(q)
	try:
		dat=''.join(map(lambda x: chr(x % 256), outBA))
		curs.execute(q,[dat,dat,str(jit)])
		db.commit()
	except:
		db.rollback()
		print("Error Adding faceEncoding entry")
		print(sys.exc_info())
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
		encodeFile(path+f,True,knownJit)
		print("Loaded(Known): "+f)

def loadUnKnownFolder(path):
	files = []
	for (dirpath, dirnames, filenames) in os.walk(path):
		files.extend(filenames)
		break
	for f in files:
		encodeFile(path+f,False,unknownJit)
		print("Loaded(Unknown): "+f)

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

def getUnknownFileList():
	q="select filename from faceEncoding where known=0"
	try:
		curs.execute(q,)
		unknownFiles=curs.fetchall()
		return unknownFiles
	except:
		print("Failed to fetch unknown filenames from faceEncoding")
		print(sys.exc_info())
		return None


		
def deepfind():
	minJ=getMinJit()
	if minJ>=maxJit:
		#as far as we want to go
		return -1
	if minJ<0:
		print("Error: Neg minJ")
		return -1
	q="select filename,known from faceEncoding where jitter="+str(minJ)
	try:
		curs.execute(q,)
		files=curs.fetchall()
	except:
		print("Failed to fetch files with min jitter")
		print(sys.exc_info())
		return None
	for f,k in files:
		encodeFile(f,k,minJ+1)
	matchScore=findMinKnownRelation(None)-.001
	print("Min Score Between Known People(minus .001)")
	print(matchScore)
	processUnknown(matchScore)
	print("Unknowns Processed")
	sortPictures()
	print("Images Sorted")
	return 0
	

def processUnknown(limit):
	q="select filename from faceEncoding where id=0"
	try:
		curs.execute(q,)
		unKnownFiles=curs.fetchall()
	except:
		print("Failed to fetch known filenames from faceEncoding")
		print(sys.exc_info())
		return None
	#knownFiles=getKnownFileList()#returns path and ID
	for f in unKnownFiles:
		fID,fScore=mostLikelyPerson(f)
		if fScore<=limit:
			setID(f,fID)
	
def sortPictures():
	shutil.rmtree("sorted/")
	os.mkdir("sorted/")
	known=getKnownFileList()
	for f,i in known:
		if not os.path.isdir("sorted/"+str(i)):
			os.mkdir("sorted/"+str(i))
	if not os.path.isdir("sorted/0"):
			os.mkdir("sorted/0")
	q="select id,filename from faceEncoding where known=0"
	try:
		curs.execute(q,)
		files=curs.fetchall()
	except:
		print("Failed to fetch unknown filenames and ID from faceEncoding")
		print(sys.exc_info())
		return None
	for i,f in files:
		name=f.split("/")[-1]
		name="sorted/"+str(i)+"/"+name
		shutil.copyfile(f, name)
		
	
				
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
def findSaveFacesFromImages(path,show,upSample,printTime):
	t=time.time()
	files = []
	for (dirpath, dirnames, filenames) in os.walk(path):
		files.extend(filenames)
		break
	for f in files:
		try:
			image = face_recognition.load_image_file(path+f)
		except:
			print("Error Loading file:"),
			print(f)
			continue
		faces=findFace(image,upSample)
		print("I found {} face(s) in this photograph.".format(len(faces)))
		cnt=0
		for face in faces:
			cnt=cnt+1
			convT=time.time()
			pil_image = Image.fromarray(face)
			pil_image=pil_image.convert('L')
			pil_image.save("/home/chadg/pyFace/UnKnown/"+str(cnt)+"_"+f)

			if show:
				pil_image.show()
		os.rename(path+f,"/home/chadg/pyFace/Processed/"+f)
	if printTime:
		print("Processing images for faces took: "),
		print(time.time()-t)

def checkDBvsUnknown(path):
	ffiles=[]
	UNfiles=getUnknownFileList()
	for f in UNfiles:
		ffiles.append(f[0])
	files = []
	for (dirpath, dirnames, filenames) in os.walk(path):
		files.extend(filenames)
		break
	notAdded=[]
	unFiles=[]
	for f in files:
		unFiles.append(path+f)
	
	print(unFiles)

	for f in unFiles:
		if f not in ffiles: 
				notAdded.append(f)
	try:
		shutil.rmtree("sorted/NOFACE/")
	except:
		pass
	os.mkdir("sorted/NOFACE/")
	if len(notAdded)>0:
		print("Files in Unknown that are not in the database:"+str(len(notAdded)))
		print(notAdded)
		for f in notAdded:	
			e=encodeFile(f,False,1)
			if e is None:
				name=f.split("/")[-1]
				name="sorted/NOFACE/"+name
				shutil.copyfile(f, name)
			else:
				print("Loaded(Unknown): "+f)

def checkDBvsKnown(path):
	ffiles=[]
	KnownFiles=getKnownFileList()
	for f,i in KnownFiles:
		ffiles.append(f)
	files = []
	for (dirpath, dirnames, filenames) in os.walk(path):
		files.extend(filenames)
		break
	notAdded=[]
	unFiles=[]
	for f in files:
		unFiles.append(path+f)
	
	print(unFiles)
	print("")
	print(ffiles)
	for f in unFiles:
		if f not in ffiles: 
				notAdded.append(f)
	
				
	if len(notAdded)>0:
		print("Files in Known that are not in the database:"+str(len(notAdded)))
		print(notAdded)
		#for f in notAdded:	
		#	e=encodeFile(f,True,1)
		#	if e is None:
		#		name=f.split("/")[-1]
		#		name="sorted/NOFACE/"+name
		#		shutil.copyfile(f, name)
		#	else:
		#		print("Loaded(Known): "+f)




def processFame(frame):
	#given a frame from video, check it for faces, if there is any, save them
	faces=findFace(frame,0)
	print("I found {} face(s) in this frame.".format(len(faces)))
	cnt=0
	for face in faces:
		cnt=cnt+1
		pil_image = Image.fromarray(face)
		if show:
			pil_image.show()
		pil_image=pil_image.convert('L')
		pil_image.save("/home/chadg/pyFace/UnKnown/"+str(cnt)+"_"+str(int(time.time())))

def resetDB(full):
	#if full, then remove known ecodings are well (full rebuild), if not, leave those in place and re process unknown
	
	
	
	#delete from faceEncoding
	#rescan and ID known folder
	#rescan unknown folder
	#identify knowns
	#check?
	if full:
		q="delete from faceEncoding"
	else:
		q="delete from faceEncoding where known=0"
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
	sortPictures()
	print("Images Sorted")


		
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
	resetDB(False)
	while True:
		findSaveFacesFromImages("/home/chadg/pyFace/Other/",True,1,True)
		checkDBvsUnknown("/home/chadg/pyFace/UnKnown/")
		checkDBvsKnown("/home/chadg/pyFace/Known/")
		d=deepfind()
		try:
			if d<0:
				break
		except:
			pass
	
