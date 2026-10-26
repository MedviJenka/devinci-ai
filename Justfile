set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

dev:
    docker compose up -d --build

stop:
    docker compose down

push:
    git add .
    git commit -m "auto push"
    git push
