import requests
import json
import csv
import warnings
import configparser
import getpass
import logging
from flask import abort

logging.basicConfig(level=logging.INFO)
warnings.filterwarnings("ignore")  # just during prototype phase
global _authenticatedHeader
global _data
global JIRA_URL
# App needs to get endpoint too
JIRA_URL = 'https://sapjira.wdf.sap.corp'


def _post_issue(issue_row):
    project, subtaskOf, title, description, issueType, hours, priority, labels = issue_row.split( # noqa
        ';')
    # post the new issue
    data = {"fields": {"project": {"key": project}, "parent": {"key": subtaskOf}, "summary": title, "description": description, "issuetype": { # noqa
        "id": issueType}, "timetracking": {"originalEstimate": hours, "remainingEstimate": hours}, "priority": {"id": priority}, "labels": [labels]}} # noqa
    logging.debug('JSON sent:' + json.dumps(data))
    return requests.post(JIRA_URL + '/rest/api/2/issue', # noqa
                      data=json.dumps(data), headers=_authenticatedHeader, verify=False) # noqa


def _post_auth(username, password):
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    data = {'username': username, 'password': password}
    return data, requests.post(JIRA_URL + '/rest/auth/1/session', data=json.dumps(data), headers=headers, verify=False) # noqa


def _authenticate_header(auth_response):
    sessionJson = json.loads(auth_response.text)
    sessionId = sessionJson['session']['name'] + \
        "=" + sessionJson['session']['value']
    return {'Content-Type': 'application/json', 'Accept': 'application/json', 'cookie': sessionId} # noqa


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
    if (username == ''):
        username = str(input('Username:'))
    if (password == ''):
        password = str(getpass.getpass('Password:'))
    if (project == ''):
        project = input('Project:')
    return username, password, project


def get_issue_by_key(key):
    r = requests.get(JIRA_URL + '/rest/api/2/issue/' + key,
                     data=json.dumps(data), headers=_authenticatedHeader, verify=False) # noqa
    if (r.status_code == 200):
        issueJson = json.loads(r.text)
        title = issueJson['fields']['summary']
        print('Title: ' + title)
    elif(r.status_code == 404):
        logging.error('Issue not found')


def get_open_issues():
    config = configparser.ConfigParser()
    config.read('config.ini')
    project = config.get('jira', 'project')
    if (project == ''):
        project = input('Project:')

    jql = 'project%20%3D%20' + project + \
        '%20AND%20issuetype%20in%20subTaskIssueTypes()%20AND%20status%20in%20(Open%2C%20Reopened%2C%20%22In%20Progress%22%2C%20Blocked)' # noqa
    fields = 'parent,summary,description,assignee,issuetype,status,aggregatetimeestimate,aggregatetimespent,duedate,labels' # noqa
    # aggregatetimeoriginalestimate or timeestimate or aggregatetimeestimate?
    # aggregateprogress or progress
    # aggregatetimespent or timespent
    # workratio

    r = requests.get(JIRA_URL + '/rest/api/2/search?jql=' + jql + '&fields=' +
                     fields, data=json.dumps(_data), headers=_authenticatedHeader, verify=False) # noqa
    if (r.status_code == 200):
        issuesJson = json.loads(r.text)
        issues = issuesJson['issues']

        csv = open('open_tasks.csv', 'w')

        listTitles = []
        listTitles.append('Project')
        listTitles.append('Backlog')
        listTitles.append('Title')
        listTitles.append('Description')
        listTitles.append('issueType')
        # listTitles.append('Assignee')
        # listTitles.append('Status')
        listTitles.append('EstimatedHours')
        listTitles.append('DueDate')
        # listTitles.append('TimeSpent')
        listTitles.append('Labels')
        columnTitles = ';'.join(listTitles) + ';\n'
        csv.write(columnTitles)

        for issue in issues:
            backlog = issue['fields']['parent']['fields']['summary']
            title = issue['fields']['summary']
            print('Backlog: ' + backlog)
            print('Title: ' + title)

            if (issue['fields']['description'] is not None):
                description = issue['fields']['description']
                print('Description: ' + description)
            else:
                description = ''

            issueType = issue['fields']['issuetype']['id']

            # if (issue['fields']['assignee']!=None):
            # 	assignee = issue['fields']['assignee']['displayName']
            # 	print('Assignee: ' + assignee)
            # else: assignee = ''

            # status = issue['fields']['status']['name']
            # print('Status: : ' + status)

            if (issue['fields']['aggregatetimeestimate'] is not None):
                estimatetime = str(issue['fields']['aggregatetimeestimate'])
                print('Aggregate time estimate: ' + estimatetime)
            else:
                estimatetime = ''

            # if (issue['fields']['aggregatetimespent']!=None):
            # 	timespent = str(issue['fields']['aggregatetimespent'])
            # 	print('Aggregate time spent: ' + timespent)
            # else: timespent = ''

            if (issue['fields']['duedate'] is not None):
                duedate = issue['fields']['duedate']
                print('Duedate: ', duedate)
            else:
                duedate = ''

            if (issue['fields']['labels'] != []):
                labels = issue['fields']['labels']
                print('Labels: ', labels)
            else:
                labels = ''
            print()

            row_values = []
            row_values.append(project)
            row_values.append(backlog)
            row_values.append(title)
            row_values.append(description)
            row_values.append(issueType)
            # row_values.append(assignee)
            # row_values.append(status)
            row_values.append(estimatetime)
            row_values.append(duedate)
            # row_values.append(timespent)
            row_values.append(','.join(labels))
            row = ';'.join(row_values)
            csv.write(row + ';\n')
        csv.close()


def upload_issues(filename):
    if filename.endswith('.csv'):
        with open(filename, 'r') as csvfile:
            csv_lines = list(csv.reader(csvfile, delimiter=';'))
            for row in csv_lines[1:]:
                logging.info('csv row:' + ";".join(row))
                r = _post_issue(";".join(row))
                logging.info('Response:' + r)
    else:
        logging.error('file must be CSV')


if __name__ == 'jiraCommands':
    global _authenticatedHeader
    global _data
    _data, _authenticatedHeader = _auth()
