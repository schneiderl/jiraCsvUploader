import os
from flask import Flask
from flask_restful import Api
from flask import request
from flask import abort
from flask_cors import CORS
import requests
import json
import csv
import warnings
import logging
import getpass
import urllib

logging.basicConfig(level=logging.INFO)
_app = Flask(__name__)
_api = Api(_app)
CORS(_app)
warnings.filterwarnings("ignore")  # just during prototype phase
port = int(os.getenv("PORT", 9099))
global _authenticatedHeader
global _data
global JIRA_URL
JIRA_URL = 'https://sapjira.wdf.sap.corp'


# FRONT-END COMUNICATION METHODS
@_app.route('/api/createtasks', methods=['POST', 'OPTIONS'])
def _parse_request():

    if request.method == 'OPTIONS':
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}  # noqa
    # file = request.files['file']

    r = _get_auth_from_request()[1]
    if(r.status_code == 200):
        global _authenticatedHeader
        _authenticatedHeader = _authenticate_header(r)
        read = request.data.decode('utf-8')

        lines = read.splitlines()  # no good
        for row in lines[1:]:
            logging.info('row: ' + row)
            r = _post_issue(row)
            logging.info(r)
    else:
        abort(403)

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}  # noqa


def _get_auth_from_request():
    username = request.authorization['username']
    password = request.authorization['password']
    return _post_auth(username, password)


@_app.route('/api/authenticate', methods=['POST', 'OPTIONS'])
def _authenticate():
    if request.method == 'OPTIONS':
        json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    # TO_DO: Authenticate and save the session


# BACK_END METHODS
def _post_issue(issue_row):
    row = issue_row.split(';')

    project = row[0]
    subtaskOf = row[1]
    title = row[2]
    description = row[3]
    issueType = row[4]
    hours = row[5]
    priority = row[6]
    labels = row[7].replace(' ', '').split(',')

    data = {
        'fields': {
            'project': {
                'key': project
            },
            'parent': {
                'key': subtaskOf
            },
            'summary': title,
            'description': description,
            'issuetype': {
                'id': issueType
            },
            'timetracking': {
                'originalEstimate': hours,
                'remainingEstimate': hours
            },
            'priority': {
                'id': priority
            },
            'labels': labels
        }
    }

    logging.debug('JSON sent:' + json.dumps(data))
    return requests.post(JIRA_URL + '/rest/api/2/issue',  # noqa
                      data=json.dumps(data), headers=_authenticatedHeader, verify=False)  # noqa


def _post_backlog(project, title):
    data = {
        'fields': {
            'project': {
                'key': project
            },
            'summary': title,
            'issuetype': {
                'id': '6'
            }
        }
    }
    logging.debug('JSON sent:' + json.dumps(data))
    return requests.post(JIRA_URL + '/rest/api/2/issue',  # noqa
                      data=json.dumps(data), headers=_authenticatedHeader, verify=False)  # noqa


def _post_auth(username, password):
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    data = {'username': username, 'password': password}
    return data, requests.post(JIRA_URL + '/rest/auth/1/session', data=json.dumps(data), headers=headers, verify=False)  # noqa


def _authenticate_header(auth_response):
    sessionJson = json.loads(auth_response.text)
    sessionId = sessionJson['session']['name'] + \
        '=' + sessionJson['session']['value']
    return {'Content-Type': 'application/json', 'Accept': 'application/json', 'cookie': sessionId}  # noqa


def get_backlog_key_by_summary(project, title):
    jql = 'project= "' + project + '"AND summary~"' + title + '"AND issuetype="Backlog Item"'  # noqa
    fields = 'summary'
    jql = urllib.parse.quote(jql) + '&fields=' + fields

    r = requests.get(JIRA_URL + '/rest/api/2/search?jql=' + jql , data=json.dumps(_data), headers=_authenticatedHeader, verify=False)  # noqa
    if (r.status_code == 200):
        issuesJson = json.loads(r.text)
        logging.debug('Backlogs found:' + json.dumps(issuesJson))
        for issue in issuesJson['issues']:
            jira_title = issue['fields']['summary']
            if title == jira_title:
                logging.debug('Backlog matched:' + json.dumps(issue['key']))
                return issue['key']
        return None
    else:
        logging.error('Backlog not found')

# COMMAND LINE METHODS


def upload_issues(filename):
    if filename.endswith('.csv'):
        backlogs = {}

        with open(filename, 'r') as csvfile:
            csv_lines = list(csv.reader(csvfile, delimiter=';'))
            for row in csv_lines[1:]:
                logging.info('csv row:' + ';'.join(row))
                project = row[0]
                backlog_summary = row[1]
                keys = (project, backlog_summary)
                if (keys not in backlogs):
                    backlog_key = get_backlog_key_by_summary(project, backlog_summary)  # noqa
                    if (backlog_key is None):
                        r = _post_backlog(project, backlog_summary)
                        if (r.status_code == 200 or r.status_code == 201):
                            logging.info('Backlog successfully created')
                            jsonResponse = json.loads(r.text)
                            backlogs[keys] = jsonResponse['key']
                            logging.debug('JSON Response: ' + json.dumps(jsonResponse))  # noqa
                        else:
                            logging.error('Backlog not created: ' + str(r))
                    else:
                        backlogs[keys] = backlog_key
                else:
                    logging.debug('Backlog buffered')

                # Replace Backlog Summary with key
                row[1] = backlogs[keys]
                r = _post_issue(';'.join(row))
                if (r.status_code == 200 or r.status_code == 201):
                    logging.info('Subtask successfully created')
                else:
                    logging.error('Subtask not created: ' + str(r))
                    jsonResponse = json.loads(r.text)
                    logging.debug('JSON Response: ' + json.dumps(jsonResponse))  # noqa
    else:
        logging.error('file must be CSV')


def _auth():
    username, password = _get_config()
    data, auth_response = _post_auth(username, password)
    if (auth_response.status_code == 200):
        logging.info('authenticated')
        return data, _authenticate_header(auth_response)
    else:
        abort(403)


def _get_config():
    username = str(input('Username:'))
    password = str(getpass.getpass('Password:'))
    return username, password


def get_issue_by_key(key):
    r = requests.get(JIRA_URL + '/rest/api/2/issue/' + key,
                     data=json.dumps(_data), headers=_authenticatedHeader, verify=False)  # noqa
    if (r.status_code == 200):
        issueJson = json.loads(r.text)
        title = issueJson['fields']['summary']
        print('Title: ' + title)
    elif(r.status_code == 404):
        logging.error('Issue not found')


if __name__ == '__main__':
    _app.run(host='0.0.0.0', port=port)


if __name__ == 'jiraUploader':
    global _authenticatedHeader
    global _data
    _data, _authenticatedHeader = _auth()
