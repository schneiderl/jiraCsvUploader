from flask import Flask
import os
from flask_restful import Resource, Api
from flask import request
from flask.json import jsonify
from flask import abort
import requests
import json
import base64
import csv
import warnings
from flask_cors import CORS

app = Flask(__name__)
api = Api(app)
CORS(app)
warnings.filterwarnings("ignore") #just during prototype phase
port = int(os.getenv("PORT", 9099))

@app.route('/api/createtasks', methods=['POST', 'OPTIONS'])
def parse_request():
	
	if request.method=='OPTIONS':
		return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 
	#file = request.files['file']
	
	r = __get_auth_from_request()
	if(r.status_code==200):
		authenticatedHeader = __authenticate_header(r)
		read = request.data.decode('utf-8')
		
		lines = read.splitlines() #no good
		for row in lines[1:]:
			print(row)
			r = __post_issue(row, authenticatedHeader)
			print(r)
 				
	elif (r.status_code==403):
		abort(403)
	else:
		abort(403)

	return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

def __post_issue(issue_row, authenticatedHeader):
	project, subtaskOf, title, description, issueType, hours, labels= issue_row.split(';')
	#post the new issue
	data = { "fields": {"project":{ "key": project}, "parent":{"key": subtaskOf}, "summary": title,"description": description, "issuetype": {"id": issueType}, "timetracking":{"originalEstimate":hours, "remainingEstimate":hours}, "labels":[labels]}}
	print(data)
	r = requests.post('https://sapjira.wdf.sap.corp/rest/api/2/issue', data=json.dumps(data), headers=authenticatedHeader, verify=False)

def __get_auth_from_request():
	username = request.authorization['username']
	password = request.authorization['password']
	headers = { 'Content-Type': 'application/json', 'Accept':'application/json'}
	data = {'username': username, 'password':password}
	return requests.post('https://sapjira.wdf.sap.corp/rest/auth/1/session', data=json.dumps(data), headers=headers, verify=False)

def __authenticate_header(auth_response):
	sessionJson = json.loads(auth_response.text)
	sessionId = sessionJson['session']['name'] + "=" + sessionJson['session']['value']
	return {'Content-Type': 'application/json', 'Accept':'application/json', 'cookie': sessionId}

@app.route('/')
def hello_world():
    return 'fala queridos'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)	

