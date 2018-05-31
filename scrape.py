#!/usr/bin/env python3



import urllib.request
import image_scraper

base="https://www.co.benton.or.us/"
savedImages="scrapedPics/"

urlsToScrape=[]

count=0
def scrape(url):
	print("Count:"),
	print(count)
	with urllib.request.urlopen(url) as resp:
		html=resp.read()
		html=str(html)
		#print(html)
		html=html.split("<")
	for line in html:
		if "href" in line:
			print(line)
			try:
				el=line.split('="')
				wa=el[1]
				wa=wa.split('"')
				addressToAdd=wa[0]
				if "www" not in addressToAdd:
					addressToAdd=base+addressToAdd
				urlsToScrape.append(addressToAdd)
			except:
				print("FAILED:"),
				print(line)




scrape(base+"sheriff/most-wanted")
while len(urlsToScrape)>0:
	scrape(urlsToScrape[0])
	urlsToScrape.remove(urlsToScrape[0])
