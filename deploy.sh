docker build . --platform linux/amd64 -t  discord-bot
docker tag discord-bot gcr.io/${PROJECT_ID}/discord-bot:latest 
docker push gcr.io/${PROJECT_ID}/discord-bot:latest 
# TODO: include gcloud deploy
