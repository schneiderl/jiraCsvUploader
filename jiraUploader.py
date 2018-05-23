from flask import Flask
import os
from flask_restful import Api
from flask import request
from flask import abort
import json
import warnings
from flask_cors import CORS
from jiraCommands import _post_issue
from jiraCommands import _authenticate_header
from jiraCommands import _post_auth
import logging

logging.basicConfig(level=logging.INFO)
_app = Flask(__name__)
_api = Api(_app)
CORS(_app)
warnings.filterwarnings("ignore")  # just during prototype phase
port = int(os.getenv("PORT", 9099))
global _authenticatedHeader
global _data


@_app.route('/api/createtasks', methods=['POST', 'OPTIONS'])
def _parse_request():

    if request.method == 'OPTIONS':
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    #file = request.files['file']

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

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


def _get_auth_from_request():
    username = request.authorization['username']
    password = request.authorization['password']
    return _post_auth(username, password)


if __name__ == '__main__':
    _app.run(host='0.0.0.0', port=port)
