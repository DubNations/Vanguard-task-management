"""E2E test: Member 全链路领取流程 (clean run)"""
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seedteam.settings')
os.environ['DJANGO_ENV'] = 'local'
os.environ['DJANGO_SECRET_KEY'] = 'dev-secret-key'
os.environ['JWT_SIGNING_KEY'] = 'dev-secret-key'

import django; django.setup()
import requests

BASE = 'http://127.0.0.1:8000/api/v1'
PASS = FAIL = 0

def ok(label, cond, extra=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  PASS: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label} {extra}')

def login(email, pwd):
    r = requests.post(f'{BASE}/auth/login/', json={'email': email, 'password': pwd})
    if r.status_code != 200:
        return None
    token = r.json().get('access', '')
    return {'Authorization': f'Bearer {token}'}

def api(method, path, headers, data=None):
    return getattr(requests, method)(f'{BASE}{path}', json=data, headers=headers)

# ========== 1: Leader 创建两种揭榜任务 ==========
print('='*60)
print('STEP 1: Leader 创建揭榜任务')
print('='*60)
lh = login('leader@seedteam.local', 'Test123456')
assert lh, 'Leader login failed'

r = api('post', '/tasks/', lh, {
    'title': '自由揭榜任务', 'description': 'test',
    'priority': 'MEDIUM', 'task_mode': 'FREE_CLAIM', 'reward_points': 100,
})
ok('创建 FREE_CLAIM 201', r.status_code == 201)
fc = r.json() if r.status_code == 201 else {}
fc_id = fc.get('id', '')
ok('FREE_CLAIM id存在', bool(fc_id))

r = api('post', '/tasks/', lh, {
    'title': '固定揭榜任务', 'description': 'test',
    'priority': 'HIGH', 'task_mode': 'FIXED_CLAIM', 'max_claimers': 2, 'reward_points': 50,
})
ok('创建 FIXED_CLAIM 201', r.status_code == 201)
fx = r.json() if r.status_code == 201 else {}
fx_id = fx.get('id', '')
ok('FIXED_CLAIM id存在', bool(fx_id))

# ========== 2: Member 列表可见 + can_claim ==========
print('\n' + '='*60)
print('STEP 2: Member 列表')
print('='*60)
mh = login('member@seedteam.local', 'Test123456')
assert mh, 'Member login failed'

r = api('get', '/tasks/', mh)
ok('列表 200', r.status_code == 200)
tasks = {t['title']: t for t in r.json().get('results', [])}
ok('FREE_CLAIM 在列表', '自由揭榜任务' in tasks)
ok('FIXED_CLAIM 在列表', '固定揭榜任务' in tasks)
ok('FREE_CLAIM can_claim=True', tasks.get('自由揭榜任务', {}).get('can_claim') is True)
ok('FIXED_CLAIM can_claim=True', tasks.get('固定揭榜任务', {}).get('can_claim') is True)

# ========== 3: Member 看板 ==========
print('\n' + '='*60)
print('STEP 3: Member 看板')
print('='*60)
r = api('get', '/tasks/kanban/', mh)
ok('看板 200', r.status_code == 200)
if r.status_code == 200:
    kanban_fc = kanban_fx = None
    for col in r.json().values():
        for t in col.get('tasks', []):
            if t['id'] == fc_id: kanban_fc = t
            if t['id'] == fx_id: kanban_fx = t
    ok('看板有 FREE_CLAIM', kanban_fc is not None)
    ok('看板有 FIXED_CLAIM', kanban_fx is not None)
    ok('看板 FC can_claim', kanban_fc and kanban_fc.get('can_claim') is True)
    ok('看板 FX can_claim', kanban_fx and kanban_fx.get('can_claim') is True)

# ========== 4: Member 详情页 + 子资源 ==========
print('\n' + '='*60)
print('STEP 4: Member 详情页')
print('='*60)
r = api('get', f'/tasks/{fc_id}/', mh)
ok('FREE_CLAIM 详情 200', r.status_code == 200)
ok('详情 can_claim=True', r.json().get('can_claim') is True)
ok('详情 status=PENDING', r.json().get('status') == 'PENDING')

r = api('get', f'/tasks/{fc_id}/history/', mh)
ok('历史 200', r.status_code == 200)
r = api('get', f'/tasks/{fc_id}/comments/', mh)
ok('评论 200', r.status_code == 200)
r = api('get', f'/files/list/{fc_id}/', mh)
ok('文件列表 200', r.status_code == 200)
r = api('get', f'/tasks/{fc_id}/participants/', mh)
ok('参与者列表 200', r.status_code == 200)

r = api('get', f'/tasks/{fx_id}/', mh)
ok('FIXED_CLAIM 详情 200', r.status_code == 200)
ok('FIXED 详情 can_claim=True', r.json().get('can_claim') is True)

# ========== 5: Member 领取 FREE_CLAIM ==========
print('\n' + '='*60)
print('STEP 5: 领取 FREE_CLAIM')
print('='*60)
r = api('post', f'/tasks/{fc_id}/claim/', mh)
ok('领取 201', r.status_code == 201)
if r.status_code == 201:
    ok('status=ACCEPTED', r.json().get('status') == 'ACCEPTED')

r = api('get', f'/tasks/{fc_id}/', mh)
ok('领取后 IN_PROGRESS', r.json().get('status') == 'IN_PROGRESS')
ok('领取后 can_claim=False', r.json().get('can_claim') is False)

r = api('post', f'/tasks/{fc_id}/claim/', mh)
ok('重复领取 400', r.status_code == 400)

# ========== 6: Member 领取 FIXED_CLAIM ==========
print('\n' + '='*60)
print('STEP 6: 领取 FIXED_CLAIM')
print('='*60)
r = api('post', f'/tasks/{fx_id}/claim/', mh)
ok('领取 201', r.status_code == 201)

r = api('get', f'/tasks/{fx_id}/', mh)
ok('FIXED 领取后仍 PENDING(未满)', r.json().get('status') == 'PENDING')
ok('FIXED current_claimers=1', r.json().get('current_claimers') == 1)

# ========== 7: Admin 领取 FIXED (额满) ==========
print('\n' + '='*60)
print('STEP 7: Admin 领取 FIXED (额满)')
print('='*60)
ah = login('admin@seedteam.local', 'Test123456')
assert ah, 'Admin login failed'

# 新建一个 FIXED_CLAIM 任务来测额满
r = api('post', '/tasks/', lh, {
    'title': '额满测试任务', 'description': 'test',
    'priority': 'LOW', 'task_mode': 'FIXED_CLAIM', 'max_claimers': 2, 'reward_points': 10,
})
ok('创建额满测试任务 201', r.status_code == 201)
fx2 = r.json() if r.status_code == 201 else {}
fx2_id = fx2.get('id', '')
ok('额满任务 id存在', bool(fx2_id))

if fx2_id:
    # member 领
    r = api('post', f'/tasks/{fx2_id}/claim/', mh)
    ok('member 领额满任务 201', r.status_code == 201)
    # admin 领
    r = api('post', f'/tasks/{fx2_id}/claim/', ah)
    ok('admin 领额满任务 201', r.status_code == 201)
    # 查看 current_claimers
    r = api('get', f'/tasks/{fx2_id}/', lh)
    ok('额满后 current_claimers=2', r.json().get('current_claimers') == 2)
    # 第三人领 → 失败
    ah2 = login('leader2@seedteam.local', 'Test123456')
    if ah2:
        r = api('post', f'/tasks/{fx2_id}/claim/', ah2)
        ok('额满后第三人 400', r.status_code == 400)

# ========== 8: 看板领取 ==========
print('\n' + '='*60)
print('STEP 8: 看板直接领取')
print('='*60)
r = api('post', '/tasks/', lh, {
    'title': '看板领取测试', 'description': 'test',
    'priority': 'MEDIUM', 'task_mode': 'FREE_CLAIM', 'reward_points': 10,
})
ok('创建看板测试任务 201', r.status_code == 201)
kb_task = r.json() if r.status_code == 201 else {}
kb_id = kb_task.get('id', '')
if kb_id:
    r = api('post', f'/tasks/{kb_id}/claim/', mh)
    ok('看板领取 201', r.status_code == 201)
    r = api('get', f'/tasks/{kb_id}/', mh)
    ok('看板领取后 IN_PROGRESS', r.json().get('status') == 'IN_PROGRESS')

# ========== SUMMARY ==========
print('\n' + '='*60)
print(f'结果: PASS={PASS}, FAIL={FAIL}')
print('='*60)
sys.exit(0 if FAIL == 0 else 1)
