from flask import Flask, render_template, request, jsonify, redirect, Response, g
from github import Github, Auth, GithubIntegration
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from git import Repo
import subprocess
import json

# Load environment variables from .env file
load_dotenv()
PRIVATE_KEY = os.getenv('GITHUB_PRIVATE_KEY')
WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET')
APP_IDENTIFIER = os.getenv('GITHUB_APP_IDENTIFIER')
if PRIVATE_KEY is None:
  raise ValueError("GITHUB_PRIVATE_KEY environment variable not set.")

PRIVATE_KEY= PRIVATE_KEY.replace('\\n', '\n')

def get_payload_request(request):
  data = request.get_json()
  g.payload = data
  return

def authenticate_app():
   return

def authenticate_installation(payload):
  g.installation_id = payload["installation"]['id']

  auth = Auth.AppAuth(int(APP_IDENTIFIER), PRIVATE_KEY).get_installation_auth(int(g.installation_id))
  g.installation_client = Github(auth=auth)


def verify_webhook_signature():
  #print(request.json)
  return

def create_check_run():
    g.repo = g.installation_client.get_repo(g.payload['repository']['full_name']) 
    if g.payload.get('check_run') == None:
      head_sha = g.payload['check_suite']['head_sha']
    else:
      head_sha = g.payload['check_run']['head_sha']
    g.repo.create_check_run("Octo RuboCop", head_sha)

def initiate_check_run():
   g.repo = g.installation_client.get_repo(g.payload['repository']['full_name']) 
   check_run = g.repo.get_check_run(g.payload['check_run']['id'])
   check_run.edit(status="in_progress")
   # Run Ci test
   full_repo_name = g.payload['repository']['full_name']
   repository = g.payload['repository']['name']
   head_sha = g.payload['check_run']['head_sha']
   """
   clone_repository(full_repo_name, repository, head_sha)
   # RUn robocop
   g.report = subprocess.run(
    ['rubocop', repository, '--format', 'json'], 
    text=True,         # Return output as a string (Python 3.7+)
    capture_output=True # Capture stdout and stderr
)
   print(g.report)
   subprocess.run(
    ['rm', '-rf', repository], 
    check=True
)
   g.output = json.loads(g.report)
   """
   check_run.edit(status="completed", conclusion="success")

def clone_repository(full_repo_name, repository, ref):
   url = f'https://x-access-token:{g.installation_token}@github.com/{full_repo_name}.git'
   g.repo = Repo.clone_from(url, repository)
   pwd = os.getcwd()
   os.chdir(repository)
   g.repo.remote().pull()
   g.repo.git.checkout(ref)
   os.chdir(pwd)


app = Flask(__name__)

@app.before_request
def before_request():
    get_payload_request(request)
    verify_webhook_signature()

    authenticate_app()
    authenticate_installation(g.payload)
    return

@app.post("/event_handler")
def event_handler():
  event_type = request.headers.get('X_GITHUB_EVENT')
  
  if event_type == 'check_suite':
     
     action = g.payload['action']
     if action == 'requested' or action == 'rerequested':
        create_check_run()
  elif event_type == "check_run":
     
     if str(g.payload['check_run']['app']['id']) == APP_IDENTIFIER:
        action = g.payload['action']
        if action == 'created':
           initiate_check_run()
        elif action == "rerequested":
           create_check_run()
  return "Success", 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000, debug=True)


