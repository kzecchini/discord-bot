import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import logging
from typing import List, Optional


# basic config as env vars
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
APPLICATION_ID = os.getenv('APPLICATION_ID')
DATA_PATH = os.getenv('DATA_PATH', './data')
STATUS_NAME = os.getenv('STATUS_NAME', "just vibing")
FIRESTORE_HOST = os.getenv('FIRESTORE_HOST', 'localhost')
FIRESTORE_PORT = os.getenv('FIRESTORE_PORT', '8026')



# TODO implement bot commands
# global discord objects
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(application_id=APPLICATION_ID, intents=intents)
tree = app_commands.CommandTree(client)


def setup_logging():
    # use default discord logger
    discord.utils.setup_logging(level=logging.INFO)


@tree.command()
async def join_voice_channel(interaction: discord.Interaction, channel: str):
    for voice_channel in interaction.guild.voice_channels:
        if channel == voice_channel.name:
            break
    
    await voice_channel.connect()

    await interaction.response.send_message(f"Connected to {channel}!")


@join_voice_channel.autocomplete('channel')
async def channel_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    channels = interaction.guild.voice_channels
    return [
        app_commands.Choice(name=channel.name, value=channel.name)
        for channel in channels if current.lower() in channel.name.lower()
    ]


@tree.command()
async def disconnect_from_voice(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is not None:
        voice_channel_name = voice_client.channel.name
        await voice_client.disconnect()
        await interaction.response.send_message(f"Disconnected from {voice_channel_name}!")
    else:
        await interaction.response.send_message("Not connected to any channels in this server!")


@tree.command()
async def add_intro_clip(interaction: discord.Interaction, youtube_link: str, start_time: str, end_time: str, clip_name: Optional[str]):
    # TODO: logic for downloading via youtube_dl and storing in db
    # should be unique to guild + user + clip_name, limited at 5 clips per person
    await interaction.response.send_message(f"Creating your intro clip! This might take a few minutes to start working")


@tree.command()
async def choose_intro_clip(interaction: discord.Interaction, clip_name: str):
    # TODO
    await interaction.response.send_message(f"Your intro clip is now {clip_name}")


@choose_intro_clip.autocomplete("clip_name")
async def clip_name_autocomplete(interaction: discord.Interaction, current: str):
    # TODO: get clip names from db
    all_clip_names = ['placeholder']
    return [
        app_commands.Choice(name=clip_name, value=clip_name) 
        for clip_name in all_clip_names if current.lower() in clip_name.lower() 
    ]

@client.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.id == client.user.id:
        return
    
    if before.channel == after.channel:
        logging.warning("before and after channels the same - something is wrong")
        return

    for voice_client in client.voice_clients:
        # when we hit the channel - process
        if (voice_client.channel == after.channel):
            vc = voice_client
            if not voice_client.is_connected():
                logging.info('voice_client not connected, connecting!')
                vc = await voice_client.channel.connect()
            # TODO: get and play clip
            logging.info(f"Playing intro clip for user {member.name} in channel {after.channel.name}")
            break


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
