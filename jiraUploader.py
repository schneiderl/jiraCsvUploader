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
logging = logging.getLogger(os.path.basename(__file__))
_app = Flask(__name__)
_api = Api(_app)
CORS(_app)
warnings.filterwarnings("ignore")  # just during prototype phase
port = int(os.getenv("PORT", 9099))
global JIRA_URL
JIRA_URL = 'https://jira.com'


@_app.route('/api/createtasks', methods=['POST', 'OPTIONS'])
def _parse_request():

    if request.method == 'OPTIONS':
        return json.dumps({'success': True}), 200, \
                          {'ContentType': 'application/json'}

    try:
        authenticated_header = _authorize()
    except ConnectionError as err:
        response = {'Authentication': False, 'Jira Status Code': err.args}
        return json.dumps(response), 401, {'ContentType': 'application/json'}
    # read = request.data.decode('utf-8')
    request_json = request.get_json()  # TODO: fix encoding/decoding
    logging.debug('JSON read:' + json.dumps(request_json))
    try:
        create_issues(request_json, authenticated_header)
    except ConnectionError as err:
        response = {'Tasks Creation': False, 'Jira Status Code': err.args}
        return json.dumps(response), 999, {'ContentType': 'application/json'}

    return json.dumps({'success': True}), 200, {'ContentType':
                                                'application/json'}


def _authorize():
    username = request.authorization['username']
    password = request.authorization['password']
    r = _post_auth(username, password)
    if (r.status_code == 200):
        logging.info('authenticated')
        return _authenticate_header(r)
    logging.error('Authentication Error')
    raise ConnectionError(r.status_code)


def _post_auth(username, password):
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    data = {'username': username, 'password': password}
    return requests.post(JIRA_URL + '/rest/auth/1/session',
                         data=json.dumps(data), headers=headers, verify=False)


def _authenticate_header(auth_response):
    sessionJson = json.loads(auth_response.text)
    sessionId = sessionJson['session']['name'] + \
        '=' + sessionJson['session']['value']
    return {'Content-Type': 'application/json',
            'Accept': 'application/json', 'cookie': sessionId}


def create_issues(tasks_json, auth):
    for task in tasks_json['tasks']:
        logging.info('Next Task:' + ';' + json.dumps(task))
        project = task['fields']['project']['key']
        parent = task['fields']['parent']['key']
        keys = (project, parent)
        backlogs = {}

        if (keys not in backlogs):
            backlog_key = get_backlog_key_by_summary(project, parent, auth)
            if (backlog_key is None):
                r = _post_backlog(project, parent, auth)
                if (r.status_code == 200 or r.status_code == 201):
                    logging.info('Backlog successfully created')
                    jsonResponse = json.loads(r.text)
                    backlogs[keys] = jsonResponse['key']
                    logging.debug('JSON Response: ' + json.dumps(jsonResponse))
                else:
                    logging.error('Backlog not created: ' + str(r))
                    raise ConnectionError('Backlog not created')
            else:
                backlogs[keys] = backlog_key
        else:
            logging.debug('Backlog buffered')

        # Replace Backlog Summary with key
        task['fields']['parent']['key'] = backlogs[keys]
        r = _post_issue(task, auth)
        if (r.status_code == 200 or r.status_code == 201):
            logging.info('Subtask successfully created')
        else:
            logging.error('Subtask not created: ' + str(r))
            jsonResponse = json.loads(r.text)
            logging.debug('JSON Response: ' + json.dumps(jsonResponse))
            raise ConnectionError('Task not created')

    return


def get_backlog_key_by_summary(project, title, auth):
    jql = 'project= "' + project + '"AND summary~"' + title + '"AND issuetype='
    jql += '"Backlog Item" AND status in ("Open", "In Progress", "Reopened")'
    fields = 'summary'
    jql = urllib.parse.quote(jql) + '&fields=' + fields

    r = requests.get(JIRA_URL + '/rest/api/2/search?jql=' + jql,
                     headers=auth, verify=False)
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
        logging.info('Backlog not found: ' + title)


def _post_backlog(project, title, auth):
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
    logging.debug('JSON "create backlog":' + json.dumps(data))
    return requests.post(JIRA_URL + '/rest/api/2/issue',
                         data=json.dumps(data), headers=auth, verify=False)


def _post_issue(task_json, auth):
    logging.debug('JSON "create issue":' + json.dumps(task_json))
    return requests.post(JIRA_URL + '/rest/api/2/issue',
                         data=json.dumps(task_json),
                         headers=auth, verify=False)


def get_issue_by_key(key, auth):
    r = requests.get(JIRA_URL + '/rest/api/2/issue/' + key,
                     headers=auth, verify=False)
    if (r.status_code == 200):
        issueJson = json.loads(r.text)
        title = issueJson['fields']['summary']
        print('Title: ' + title)
    elif(r.status_code == 404):
        logging.error('Issue not found')


if __name__ == '__main__':
    _app.run(host='0.0.0.0', port=port)
