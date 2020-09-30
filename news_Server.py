from flask import Flask,jsonify,request
from datetime import datetime
from pymongo import MongoClient
import re

client=MongoClient("mongodb://localhost:27017/")
db=client['test']
Collection=db['news']
client.server_info()



app=Flask(__name__)

@app.route('/')
def show():
	date=datetime.date(datetime.now())
	date=str(date)
	feeds=Collection.find({'publish_date':{'$eq': date}})
	return jsonify(list(feeds))

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

@app.route('/stats/overdate')
def overdate():
	results=[]
	temp=Collection.distinct('source')
	dates=Collection.distinct('publish_date')
	for src in temp:
		src_stats={}
		for date in sorted(dates,reverse=True):
			temp=Collection.count_documents({'source': src,'publish_date': date})
			if temp > 0:
				src_stats[date]=temp
		res={}
		res[src]=src_stats
		results.append(res)
	return jsonify(results)


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

@app.route('/companyCode/<code>')
def getCompanyDetailsCode(code):
	results=[]
	temp=Collection.find({'Security':{'$eq': code}})
	for i in temp:
		results.append(i)
	return jsonify(results)
 
@app.route('/date/<dateres>')
def GetByDate(dateres):
	results=[]
	temp=Collection.find({'publish_date':{'$eq': dateres}})
	for i in temp:
		results.append(i)
	return jsonify(results)

@app.route('/company',methods=['GET', 'POST']) #allow both GET and POST requests
def form_example():
    if request.method == 'POST': #this block is only entered when the form is submitted
        return getCompanyDetails(request.form['name'])

    return '''<form method="POST">
                  Company : <input type="text" name="name"><br>
                  <input type="submit" value="Submit"><br>
              </form>'''

app.run(port=7000,debug=True)

