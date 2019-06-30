# Discord Bot

A basic discord bot designed to have some fun with friends. 

Utilizes garflied comics data scraped from previous machine learning reverse image search project.

### Commands:
```
!join 
- join voice channel you are connected to

!garfield 
- display a random garfield comic

!clip <youtube_url> <start_time> <end_time> 
- update the voice clip to play when you join voice channel where the bot is present
- example: !clip https://www.youtube.com/watch?v=Pmf1TWwXrz4 1:39 1:43
```

### Passive checks:
- Will play a short mp3 file when a user joins a voice channel the bot is currently on. If a user has not called the `!clip` command, one of the default voice clips will play.
- Analyzes sentiment of messages containing my friend's favorite characters and responds based on the sentiment.
