echo $GITHUB_PERSONAL_ACCESS_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
docker build . --platform linux/amd64 -t discord-bot:latest
docker tag discord-bot:latest ghcr.io/$GITHUB_USERNAME/discord-bot:latest
docker push ghcr.io/$GITHUB_USERNAME/discord-bot:latest
