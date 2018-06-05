import os
from flask import Flask
from flask_restful import Api
from flask import request
from flask import abort
from flask_cors import CORS
import requests
import json
import warnings
import logging
import configparser
import getpass

logging.basicConfig(level=logging.INFO)
_app = Flask(__name__)
_api = Api(_app)
CORS(_app)
warnings.filterwarnings("ignore")  # just during prototype phase
port = int(os.getenv("PORT", 9099))
global _authenticatedHeader
global _data
global JIRA_URL
global PROJECT
# App needs to get endpoint too
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
            logging.info(row)
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
    project, subtaskOf, title, description, issueType, hours, priority, labels = issue_row.split(  # noqa
        ';')
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
            'labels': [labels]
        }
    }

    logging.debug('JSON sent:' + json.dumps(data))
    return requests.post(JIRA_URL + '/rest/api/2/issue',  # noqa
                      data=json.dumps(data), headers=_authenticatedHeader, verify=False)  # noqa


def _post_backlog(title):
    data = {'fields': {'project': {'key': PROJECT}, 'summary': title, 'issuetype': {  # noqa
        'id': '6'}}}  # noqa
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


def get_backlog_key_by_summary(title):
    jql = 'project%20%3D%20' + PROJECT + '%20AND%20summary%20~%20"' + \
         title + '"%20AND%20issuetype%20%3D%20"Backlog%20Item"&fields='
    fields = 'summary'

    r = requests.get(JIRA_URL + '/rest/api/2/search?jql=' + jql + '&fields=' +
                     fields, data=json.dumps(_data), headers=_authenticatedHeader, verify=False)  # noqa
    if (r.status_code == 200):
        issuesJson = json.loads(r.text)
        logging.debug(json.dumps(issuesJson))
        for issue in issuesJson['issues']:
            jira_title = issue['fields']['summary']
            if title == jira_title:
                return issue['key']
        return None
    elif(r.status_code == 404):
        logging.error('Issue not found')

# COMMAND LINE METHODS


def upload_issues(filename):
    if filename.endswith('.csv'):
        backlogs = {}

        with open(filename, 'r') as csvfile:
            csv_lines = list(csv.reader(csvfile, delimiter=';'))
            for row in csv_lines[1:]:
                logging.info('csv row:' + ';'.join(row))
                backlog_summary = row[1]
                if (backlog_summary not in backlogs):
                    backlog_key = get_backlog_key_by_summary(backlog_summary)
                    if (backlog_key is None):
                        r = _post_backlog(backlog_summary)
                        if (r.status_code == 200 or r.status_code == 201):
                            logging.info('Backlog successfully created')
                            jsonResponse = json.loads(r.text)
                            backlogs[backlog_summary] = jsonResponse['key']
                            logging.debug('JSON Response: ' + json.dumps(jsonResponse))  # noqa
                        else:
                            logging.error('Backlog not created: ' + str(r))
                    else:
                        backlogs[backlog_summary] = backlog_key
                row[1] = backlogs[backlog_summary]
                r = _post_issue(';'.join(row))
                if (r.status_code == 200 or r.status_code == 201):
                    logging.info('Subtask successfully created')
                else:
                    logging.error('Subtask not created: ' + str(r))
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
    config = configparser.ConfigParser()
    config.read('config.ini')
    global JIRA_URL
    global PROJECT
    username = config.get('jira', 'username')
    password = config.get('jira', 'password')
    PROJECT = config.get('jira', 'project')
    JIRA_URL = config.get('endpoints', 'jira')
    if (username == ''):
        username = str(input('Username:'))
    if (password == ''):
        password = str(getpass.getpass('Password:'))
    if (PROJECT == ''):
        PROJECT = input('Project:')
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
