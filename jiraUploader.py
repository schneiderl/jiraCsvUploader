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
import configparser
import getpass
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
api = Api(app)
CORS(app)
warnings.filterwarnings("ignore") #just during prototype phase
port = int(os.getenv("PORT", 9099))
global authenticatedHeader
global JIRA_URL

@app.route('/api/createtasks', methods=['POST', 'OPTIONS'])
def parse_request():
	
	if request.method=='OPTIONS':
		return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 
	#file = request.files['file']
	
	r = _get_auth_from_request()
	if(r.status_code==200):
		authenticatedHeader = _authenticate_header(r)
		read = request.data.decode('utf-8')
		
		lines = read.splitlines() #no good
		for row in lines[1:]:
			print(row)
			r = _post_issue(row, authenticatedHeader)
			print(r)
 				
	elif (r.status_code==403):
		abort(403)
	else:
		abort(403)

	return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

def _post_issue(issue_row, authenticatedHeader):
	project, subtaskOf, title, description, issueType, hours, duedate, labels= issue_row.split(';')
	#post the new issue
	data = { "fields": {"project":{ "key": project}, "parent":{"key": subtaskOf}, "summary": title,"description": description, "issuetype": {"id": issueType}, "timetracking":{"originalEstimate":hours, "remainingEstimate":hours}, "duedate":duedate, "labels":[labels]}}
	print(data)
	r = requests.post('https://sapjira.wdf.sap.corp/rest/api/2/issue', data=json.dumps(data), headers=authenticatedHeader, verify=False)

def _get_auth_from_request():
	username = request.authorization['username']
	password = request.authorization['password']
	return _post_auth(username, password)

def _post_auth(username, password):
	headers = { 'Content-Type': 'application/json', 'Accept':'application/json'}
	data = {'username': username, 'password':password}
	return data, requests.post('https://sapjira.wdf.sap.corp/rest/auth/1/session', data=json.dumps(data), headers=headers, verify=False)

def _authenticate_header(auth_response):
	sessionJson = json.loads(auth_response.text)
	sessionId = sessionJson['session']['name'] + "=" + sessionJson['session']['value']
	return {'Content-Type': 'application/json', 'Accept':'application/json', 'cookie': sessionId}

def _auth():
	username, password, project = _get_config()
	data, auth_response = _post_auth(username, password)
	if (auth_response.status_code == 200):
		logging.info('authenticated')
		return data, _authenticate_header(auth_response)
	else:
		abort(403)

def _get_config():
	config = configparser.ConfigParser()
	config.read('config.ini')
	global JIRA_URL
	username = config.get('jira', 'username')
	password = config.get('jira', 'password')
	project = config.get('jira', 'project')
	JIRA_URL = config.get('endpoints', 'jira')
	if (username == ''): username = str(input('Username:'))
	if (password == ''): password = str(getpass.getpass('Password:'))
	if (project == ''): project = input('Project:')
	return username, password, project

def get_issue_by_key(key):
	r = requests.get(JIRA_URL + '/rest/api/2/issue/' + key, data=json.dumps(data), headers=authenticatedHeader, verify=False)
	if (r.status_code==200):
		issueJson = json.loads(r.text)
		title = issueJson['fields']['summary']
		logging.info('	Title: ' + title)
	elif(r.status_code==404):
		logging.error('Issue not found')

def get_open_issues():
	config = configparser.ConfigParser()
	config.read('config.ini')
	project = config.get('jira', 'project')
	if (project == ''): project = input('Project:')

	jql = 'project%20%3D%20' + project + '%20AND%20issuetype%20in%20subTaskIssueTypes()%20AND%20status%20in%20(Open%2C%20Reopened%2C%20%22In%20Progress%22%2C%20Blocked)'
	fields = 'parent,summary,description,assignee,issuetype,status,aggregatetimeestimate,aggregatetimespent,duedate,labels'
	#aggregatetimeoriginalestimate or timeestimate or aggregatetimeestimate?
	#aggregateprogress or progress
	#aggregatetimespent or timespent
	#workratio

	r = requests.get(JIRA_URL + '/rest/api/2/search?jql=' + jql + '&fields=' + fields, data=json.dumps(data), headers=authenticatedHeader, verify=False)
	if (r.status_code==200):
		issuesJson = json.loads(r.text)
		issues = issuesJson['issues']

		csv = open('open_tasks.csv', 'w')

		listTitles = []
		listTitles.append('Project')
		listTitles.append('Backlog')
		listTitles.append('Title')
		listTitles.append('Description')
		listTitles.append('issueType')
		#listTitles.append('Assignee')
		#listTitles.append('Status')
		listTitles.append('EstimatedHours')
		listTitles.append('DueDate')
		#listTitles.append('TimeSpent')
		listTitles.append('Labels')
		columnTitles = ';'.join(listTitles) + ';\n'
		csv.write(columnTitles)

		for issue in issues:
			backlog = issue['fields']['parent']['fields']['summary']
			title = issue['fields']['summary']
			print('Backlog: ' + backlog)
			print('Title: ' + title)

			if (issue['fields']['description']!=None):
				description = issue['fields']['description']
				print('Description: ' + description)
			else: description = ''

			issueType = issue['fields']['issuetype']['id']

			# if (issue['fields']['assignee']!=None):
			# 	assignee = issue['fields']['assignee']['displayName']
			# 	print('Assignee: ' + assignee)
			# else: assignee = ''

			# status = issue['fields']['status']['name']
			# print('Status: : ' + status)

			if (issue['fields']['aggregatetimeestimate']!=None):
				estimatetime = str(issue['fields']['aggregatetimeestimate'])
				print('Aggregate time estimate: ' + estimatetime)
			else:
				estimatetime = ''

			# if (issue['fields']['aggregatetimespent']!=None):
			# 	timespent = str(issue['fields']['aggregatetimespent'])
			# 	print('Aggregate time spent: ' + timespent)
			# else: timespent = ''

			#if (issue['fields']['workratio']!=None): print('Work ratio: ' + issue['fields']['workratio'])

			if (issue['fields']['duedate']!=None):
				duedate = issue['fields']['duedate']
				print('Duedate: ', duedate)
			else: duedate = ''
			
			if (issue['fields']['labels']!=[]):
				labels = issue['fields']['labels']
				print('Labels: ', labels)
			else: labels = ''
			print()

			row_values = []
			row_values.append(project)
			row_values.append(backlog)
			row_values.append(title)
			row_values.append(description)
			row_values.append(issueType)
			#row_values.append(assignee)
			#row_values.append(status)
			row_values.append(estimatetime)
			row_values.append(duedate)
			#row_values.append(timespent)
			row_values.append(','.join(labels))
			row = ';'.join(row_values)
			str(row).encode('utf-8')
			csv.write(row + ';\n')
		csv.close()

@app.route('/')
def hello_world():
    return 'fala queridos'

if __name__ == 'jiraUploader':
	global authenticatedHeader
	global data
	data, authenticatedHeader = _auth()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)	

