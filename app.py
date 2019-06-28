import discord
from discord.ext import commands
from discord.ext.commands.help import DefaultHelpCommand
import os
import sys
import time
from textblob import TextBlob
from dotenv import load_dotenv
import random
import logging

from utils import get_files, clean_message

log_fmt = "%(asctime)s %(levelname)s %(filename)s %(funcName)s: %(message)s"
logging.basicConfig(format=log_fmt, level=logging.INFO)

load_dotenv()

TOKEN = os.environ['TOKEN']
VOICE_PATH = os.environ['VOICE_PATH']
GARFIELD_PATH = os.environ['GARFIELD_PATH']

VOICE_FILES = get_files(VOICE_PATH)
GARFIELD_FILES = get_files(GARFIELD_PATH)

TOMMY_PHRASES = [
    "Trish = Trash"
]

BAD_WAIFUS = [
    "mei",
    "ruby heart",
    "trish",
    "x23",
    "juri",
    "android21",
    "android 21",
    "android 18",
    "android18"
]

# TODO implement bot commands
bot = commands.Bot(command_prefix=">>")
client = discord.Client()

@client.event
async def on_ready():
    logging.info("The bot is ready!")
    # discord.opus.load_opus()
    name = random.choice(TOMMY_PHRASES)
    logging.info("opus status: {}".format(discord.opus.is_loaded()))
    await client.change_presence(status=discord.Status.online,
                                 activity=discord.Game(name=name))

@client.event
async def on_message(message):
    # it's me! do nothing
    if message.author == client.user:
        return
    
    # basic ping
    if message.content == "Ping!":
        await message.channel.send("Pong!")

    # join current voice channel of message author
    if message.content == '!join':
        author = message.author
        if author.voice is not None:
            voice_channel = author.voice.channel
            if client.voice_clients:
                for voice_client in client.voice_clients:
                    await voice_client.move_to(voice_channel)
            else:
                await voice_channel.connect()
        else:
            msg = '{} - you must be in a voice channel for that command to work!'
            await message.channel.send(msg.format(author.mention))

    # logout the bot
    if message.content == '!logout':
        await client.logout()
    
    # display a random garfield comic
    if message.content == '!garfield':
        filename = random.choice(GARFIELD_FILES)
        logging.info("showing garfield file: {}".format(filename))
        file_obj = discord.File(filename)
        await message.channel.send(content="Here is your random Garfield!", file=file_obj)

    cleaned_msg = clean_message(message.content)
    for waifu in BAD_WAIFUS:
        if waifu in cleaned_msg:
            blob = TextBlob(message.content)
            score = blob.polarity
            # TODO change to threshold configuration values
            if score >= 0.2:
                msg = "Don't kid yourself {}, {} is a trash tier waifu!"
                msg = msg.format(message.author.mention, waifu)
                await message.channel.send(content=msg)
            elif score <= -0.2:
                msg = "Correct {}! {} is a trash tier waifu!"
                msg = msg.format(message.author.mention, waifu)
                await message.channel.send(content=msg)
            else:
                msg = ("{}, you mentioned {} in a neutral context, "
                       "but I wanted to make sure you know she is garbage.")
                msg = msg.format(message.author.mention, waifu)
                await message.channel.send(content=msg)


@client.event
async def on_voice_state_update(member, before, after):
    if member.id == client.user.id:
        logging.info("this is me! do nothing")
        return
    if client.voice_clients is None:
        logging.info("Bot must be connected to voice channel")
        return
    # check if in current channel
    for voice_client in client.voice_clients:
        vc = voice_client
        if not voice_client.is_connected():
            vc = await voice_client.channel.connect()
        # if the member is connecting to this channel from anywhere else - play a greeting!
        if (voice_client.channel == after.channel) and (before.channel != after.channel):            
            filename = random.choice(VOICE_FILES)
            logging.info("playing file: {}".format(filename))
            audio_source = discord.FFmpegPCMAudio(filename)
            # wait for user to connect to hear the full voice clip
            time.sleep(0.3)
            vc.play(audio_source)


client.run(TOKEN)
