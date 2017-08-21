import requests
import getpass 
import json
import base64
import csv
import warnings

import http.client

warnings.filterwarnings("ignore")


username = getpass.getuser()
password = getpass.getpass('Password')

headers = { 'Content-Type': 'application/json', 'Accept':'application/json'}
data = {'username': username, 'password':password}

r = requests.post('https://sapjira.wdf.sap.corp/rest/auth/1/session', data=json.dumps(data), headers=headers, verify=False)
if(r.status_code==200):

	sessionJson = json.loads(r.text)
	sessionId = sessionJson['session']['name'] + "=" + sessionJson['session']['value']

	authenticatedHeader = {'Content-Type': 'application/json', 'Accept':'application/json', 'cookie': sessionId}


	file_reader= open('csv_template.csv', "r", encoding='utf-8')
	read = csv.reader(file_reader)
	counter = 0
	for row in read :
		project, subtaskOf, title, description, issueType, hours, labels= row[0].split(';')

	
		if(counter!=0):
 			#post the new issue
 			data = { "fields": {"project":{ "key": project}, "parent":{"key": subtaskOf}, "summary": title,"description": description, "issuetype": {"id": issueType}, "timetracking":{"originalEstimate":hours, "remainingEstimate":hours}, "labels":[labels]}}
 			r = requests.post('https://sapjira.wdf.sap.corp/rest/api/2/issue/', data=json.dumps(data), headers = authenticatedHeader, verify=False)
		counter = counter+1 	
elif (r.status_code==403):
	print("User already logged in on another session")
else:
	print("Authentication error")

