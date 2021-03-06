# News Scraping Using Python

## Importing required Modules


```python
import sys
import os
import hashlib
import subprocess
import requests
import datefinder
import newspaper
import pymongo
import re
import warnings
import tldextract
import pickle
import json
import pandas as pd
```

## Importing sub modules


```python
from flask import request
from datetime import datetime
from newspaper import Article
from pymongo import MongoClient
from bs4 import BeautifulSoup as bs
from concurrent.futures import ThreadPoolExecutor
```

### Filtering Warnings


```python
warnings.filterwarnings("ignore", category=DeprecationWarning)
```

### Getting data from pickle file


```python
news=[] # global variable for storing current news feeds
file=open('symbols.pickle','rb')
file=pickle.load(file)
file=pd.DataFrame(file)
d={}    # dict for storing company details 
for i in file.index:
	d.update({file['symbol'][i]:file['company'][i]})
```

# <font color=green>Database Connection Mongodb


```python
client=MongoClient("mongodb://localhost:27017/")
db=client['test']
Collection=db['news']
```

### Inserting to database
##### Duplicates are not inserted


```python
def insert_into_db(data):
	Collection.update({'_id':data['_id']},data,upsert=True)
```

### Extracting company names/code from given link


```python
def GetCompanyName(url):
	url=url.replace('\n','')
	print(url)
	info = tldextract.extract(url)
	info='.'.join(info)
	if(info=="in.finance.yahoo.com" or info=="finance.yahoo.com"):
		url=url.split('/')
		for i in url:
			url=url+i.split('?')
		return d[url[9]],url[9]
		
	elif info=="timesofindia.indiatimes.com":
		url=url.split('/')
		sec=''
		for code in d:
			if url[4].lower() in d[code].lower():
				sec=code
				return d[sec],sec
				
		return " "," "
	elif info=="in.reuters.com":
		url=url.split('/')
		sec=url[6].split('.')[0]
		return d[sec],sec
		
	elif info=="www.reuters.com":
		url=url.split('/')
		url=url[4].split('.')
		return d[url[0]],url[0]
		
	elif info=="www.hindustantimes.com":
		url=url.split('/')
		url=url[4].replace("-"," ")
		url=url.replace("%20"," ")
		sec=''
		for code in d:
			if url.lower() in d[code].lower():
				sec=code
				break
		return d[sec],sec

		
	elif info=="www.ndtv.com":
		url=url.split('/')
		url=url[4].replace('%20',' ').split()
		url=url[0]
		sec=''
		for code in d:
			if url.lower() in d[code].lower():
				sec=code
				break
		return d[sec],sec

	else:
		return " "," "
```

### Getting Article details using ***newspaper3k.Article***


```python
def getArticle(url,company,sec_code):
	try:
		print(company,sec_code)
		article=Article(url)
		article.download()
		article.build()
		article.parse()
		article.nlp()
		ans={}
		hsh=hashlib.md5(article.title.encode())
		hsh=hsh.hexdigest()
		ans['_id']=str(hsh)
		ans['title']=str(article.title)
		ans['summary']=str(article.summary).replace('\n','')
		if article.publish_date==None:
			ans['publish_date']=str(datetime.now().date())
			ans['publish_time']=str(datetime.now().time())
		else:
			ans['publish_date']=str(article.publish_date.date())
			ans['publish_time']=str(article.publish_date.time())
		ans['authors']=article.authors
		ans['source']=str(article.source_url)
		ans['company']=company
		ans['Security']=sec_code
		ans['category']='news'
		ans['keywords']=article.keywords
		sd=[]
		st=[]
		try:
			matches = datefinder.find_dates(article.summary)
			for match in set(matches):
				sd.append(str(match.date()))
				st.append(str(match.time()))
		except:
			pass
		ans['story_dates']=sd
		ans['story_time']=st

		news.append(ans)
		insert_into_db(ans)
	except:
		pass
	print("Success - "+" "+url)
```

### Extracting Article links from Source URL


```python
def getLinks(plink):
    count=3
	links=[]
	headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'}
	res=requests.get(plink,headers=headers)
	soup=bs(res.text,'lxml')
	info = tldextract.extract(plink)
	info='.'.join(info)
	if(info=="in.finance.yahoo.com" or info=="finance.yahoo.com"):

		for i in soup.find_all(["h3","a"],class_=["Fw(b) Fz(18px) Lh(23px) LineClamp(2,46px) Fz(17px)--sm1024 Lh(19px)--sm1024 LineClamp(2,38px)--sm1024 mega-item-header-link Td(n) C(#0078ff):h C(#000) LineClamp(2,46px) LineClamp(2,38px)--sm1024 not-isInStreamVideoEnabled"]):
			links.append("https://"+info+i['href']) 
		
	elif info=="timesofindia.indiatimes.com":
		for i in soup.find_all(["div","a"],class_="content"):
			links.append("https://timesofindia.indiatimes.com"+bs(str(i),'lxml').find("a")['href'])
		
	elif info=="www.reuters.com":
		class_id="TextLabel__text-label___3oCVw TextLabel__black-to-orange___23uc0 TextLabel__medium___t9PWg MarketStoryItem-headline-2cgfz"
		for i in soup.find_all(['div','a'],class_=[class_id]):
			links.append(i['href'])
		
	elif info=="www.hindustantimes.com":
		for i in soup.find_all("div",class_="media-heading headingfour"): 
			links.append(bs(str(i),'lxml').find("a")['href'])
		
	elif info=="www.ndtv.com":
		for i in soup.find_all(['li','p','a'],class_="header fbld"):
			links.append(bs(str(i),'lxml').find("a")['href'])
	elif info=="in.reuters.com":
		for i in soup.find_all(['div','a'],class_='feature'):
			links.append("https://in.reuters.com"+bs(str(i),'lxml').find('a')['href'])
	else:
		print("Scarping not Available for this domiain")
    if len(links)>count:
		links=links[0:count]
	return links
```

### Getting links from source File
#### Using Multi-Threading to process faster


```python
def Scrape(file):
	for i in file:
		company,sec_code=GetCompanyName(i)
		count=0
		with ThreadPoolExecutor() as exe:
			k=getLinks(i)
			exe.map(getArticle,k,[company]*len(k) ,[sec_code]*len(k))
			exe.shutdown(wait=True)
```

### Dumping the JSON data into File


```python
def SaveOutput(outputpath):
	date=str(datetime.now().date())
	if not os.path.exists(outputpath+"\\"+date):
		os.makedirs(outputpath+"/"+date)
	fname=str(datetime.now())
	fname=str(datetime.now()).replace(' ','_')
	fname=fname.replace('.','-')
	fname=fname.replace(':',"-")
	with open(outputpath+"\\"+date+"\\"+fname+'.json','w') as Ofile:
		json.dump(news,Ofile,indent=3)
```

# <font color=green> Getting started <font>


```python
opath=sys.argv[1].split('=')[1]
srcList=sys.argv[2].split("=")[1]
file=open(srcList,'r')
Scrape(file)
SaveOutput(opath)
```

# <font color=green> Starting Flask</font>


```python
app=Flask(__name__)
```

### <font color=green>Routing 

#### _home page_


```python
@app.route('/')
def show():
	date=datetime.date(datetime.now())
	date=str(date)
	feeds=Collection.find({'publish_date':{'$eq': date}})
	return jsonify(list(feeds))
```

#### _statistics_


```python
@app.route('/stats')
def Stats():
	dates=Collection.distinct('publish_date')
	stats=[]
	for date in sorted(dates,reverse=True):
		date_stat={}
		sources=Collection.distinct('source')
		for src in sources:
			count=Collection.count_documents({'publish_date':date,'source':src})
			if count>0:
				date_stat[src]=count
		res={}
		res[date]=date_stat
		stats.append(res)
	return jsonify(stats)
```

#### _Getting company details by name_


```python
@app.route('/company/<name>')
def getCompanyDetails(name):
	results=[]
	temp=Collection.find({
    'company': {
        	'$regex': re.compile(r""+name+"(?i)")
   		}
	})
	for i in temp:
		results.append(i)
	return jsonify(results)
```

#### _Getting company details by company code_


```python
@app.route('/companyCode/<code>')
def getCompanyDetailsCode(code):
	results=[]
	temp=Collection.find({'Security':{'$eq': code}})
	for i in temp:
		results.append(i)
	return jsonify(results)
```

#### _Getting feeds by date_


```python
@app.route('/date/<dateres>')
def GetByDate(dateres):
	results=[]
	temp=Collection.find({'publish_date':{'$eq': dateres}})
	for i in temp:
		results.append(i)
	return jsonify(results)
```

#### Getting all companies details 


```python
@app.route('/companies')
def getAllcomp():
	dates=list(Collection.distinct('publish_date'))
	comp=list(Collection.distinct('company'))
	res=[]
	temp_res={}
	for c in comp:
		if len(c)>3:
			n=Collection.count_documents({'company':c})
			if n>0:
				temp_res[c]=n
	if len(temp_res)>0:
		res.append(temp_res)
	return jsonify(res)
```

#### Getting all companies details sorted by published date


```python
@app.route('/companiesByDate')
def getAll():
	dates=list(Collection.distinct('publish_date'))
	comp=list(Collection.distinct('company'))
	res={}
	for date in sorted(dates,reverse=True):
		temp_res={}
		for c in comp:
			n=Collection.count_documents({'publish_date':date,'company':c})
			if n>0:
				temp_res[c]=n
		if len(temp_res)>0:
			res[date]=temp_res
	return jsonify(res)
```

### <font color=green>Running Flask


```python
app.run(port=7000,debug=True)
```
