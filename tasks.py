from celery import Celery
import requests
from helpers import *
import os
from dotenv import load_dotenv
load_dotenv()
biterm_url = os.environ.get("BITERM_URL")
biterm_access_token = os.environ.get("BITERM_ACCESS_TOKEN")
broker_url = os.environ.get("BROKER_URL")
celery_database_url = os.environ.get("CELERY_DATABASE_URI")


app = Celery('task', broker=broker_url, backend=celery_database_url)


@app.task
def run(data):
    try:
        response = requests.post(
            url=f"{biterm_url}?access_token={biterm_access_token}", json=data)
        response_data = response.json()
        if response.status_code == 422:
            print({'message': response_data})
    except Exception as e:
        print(e)
    return {'message': response_data}
