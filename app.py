import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import logging
from typing import List


# basic config as env vars
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
APPLICATION_ID = os.getenv('APPLICATION_ID')
DATA_PATH = os.getenv('DATA_PATH', './data')
STATUS_NAME = os.getenv('STATUS_NAME', "just vibing")


# TODO implement bot commands
# global discord objects
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(application_id=APPLICATION_ID, intents=intents)
tree = app_commands.CommandTree(client)


def setup_logging():
    log_fmt = "%(asctime)s %(levelname)s %(filename)s %(funcName)s: %(message)s"
    logging.basicConfig(format=log_fmt, level=logging.INFO)
    discord.utils.setup_logging(level=logging.INFO)


@tree.command(name="join_voice_channel")
async def join_voice_channel(interaction: discord.Interaction, channel: str):
    # TODO: actual logic of connecting
    await interaction.response.send_message(f"you want to connect to {channel}")


@join_voice_channel.autocomplete('channel')
async def channel_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    channels = interaction.guild.voice_channels
    return [
        app_commands.Choice(name=channel.name, value=channel.name)
        for channel in channels if current.lower() in channel.name.lower()
    ]


@client.event
async def on_ready():
    setup_logging()
    
    # check we can play audio
    logging.info("Opus status: {}".format(discord.opus.is_loaded()))

    # sync command tree
    await tree.sync()

    # TODO: initialize db and instantiate connection
    
    logging.info("The bot is ready!")
    
    # go online
    await client.change_presence(status=discord.Status.online,
                                 activity=discord.Game(name=STATUS_NAME))


client.run(BOT_TOKEN)
