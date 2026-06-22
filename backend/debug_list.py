import os, sys
os.environ['DJANGO_ENV'] = 'local'
os.environ['DJANGO_SECRET_KEY'] = 'dev'
os.environ['JWT_SIGNING_KEY'] = 'dev'
os.environ['DJANGO_SETTINGS_MODULE'] = 'seedteam.settings'

import django
django.setup()

import requests
BASE = 'http://127.0.0.1:8000/api/v1'

# Login as member
r = requests.post(f'{BASE}/auth/login/', json={'email': 'member@seedteam.local', 'password': 'Test123456'})
token = r.json().get('access', '')
headers = {'Authorization': f'Bearer {token}'}

# Get list
r = requests.get(f'{BASE}/tasks/', headers=headers)
print(f'List status: {r.status_code}')
for t in r.json().get('results', []):
    print(f'  {t["task_mode"]:15} | {t["status"]:12} | can_claim={t.get("can_claim")} | {t["title"]}')
