# jiraCsvUploader
Application to upload jira issues from a .csv file

In order to make it run locally you may copy configTemplate.ini into file config.ini and update fields with the asked information.

Example usage in python interpreter:

>>> import jiraUploader as J

>>> J.upload_issues('issues.csv')



p.s: do not use - in titles 
