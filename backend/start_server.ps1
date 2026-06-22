$env:DJANGO_ENV="local"
$env:DJANGO_SECRET_KEY="dev-secret-key"
$env:JWT_SIGNING_KEY="dev-secret-key"
Set-Location "C:\Li8mu\Project\种子团队任务书\backend"
& "C:\Li8mu\Project\种子团队任务书\.venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
