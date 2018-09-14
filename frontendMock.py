import os
import logging
import csv
import requests
import json

import getpass

logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(os.path.basename(__file__))


def _get_config():
    username = str(input('Username:'))
    password = str(getpass.getpass('Password:'))
    return username, password


def upload_issues(filename, username, password):
    if not filename.endswith('.csv'):
        logging.error('file must be CSV')
        return
    elif not (os.path.isfile(filename)):
        logging.error('FileNotFoundError')
        return

    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    data = {'username': username, 'password': password}

    with open(filename, 'r') as csvfile:
        csv_lines = list(csv.reader(csvfile, delimiter=';'))

        data = {}
        data['tasks'] = []
        for row in csv_lines[1:]:
            # row(Project, Backlog; Summary, Description,
            #     IssueType, Hours, Priority, Labels)
            task = {}
            task['fields'] = {}
            task['fields']['project'] = {}
            task['fields']['project']['key'] = row[0]
            task['fields']['parent'] = {}
            task['fields']['parent']['key'] = row[1]
            task['fields']['summary'] = row[2]
            task['fields']['description'] = row[3]
            task['fields']['issuetype'] = {}
            task['fields']['issuetype']['id'] = row[4]
            task['fields']['timetracking'] = {}
            task['fields']['timetracking']['originalEstimate'] = row[5]
            task['fields']['timetracking']['remainingEstimate'] = row[5]
            task['fields']['priority'] = {}
            task['fields']['priority']['id'] = row[6]
            labels = []
            for label in row[7].split(','):
                labels.append(label.strip())
            task['fields']['labels'] = labels
            data['tasks'].append(task)
        logging.debug(' Json sent:' + json.dumps(data))
        response = requests.post('http://localhost:9099/api/createtasks',
                                 auth=(username, password),
                                 data=json.dumps(data),
                                 headers=headers, verify=False)
        print(response.text)


if(__name__ == '__main__'):
    username, password = _get_config()
    upload_issues('csv.csv', username, password)
