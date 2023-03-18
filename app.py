import asyncio
from hashlib import md5
import discord
from discord.utils import get
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
from gcloud.aio.storage import Storage
from google.cloud import firestore
from uuid import uuid4

from typing import List, Tuple

from tempfile import TemporaryDirectory
import ctypes.util

from audio import download_and_process_clip

# config
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATA_BUCKET = os.getenv('DATA_BUCKET', 'discord-bot-storage')
STATUS_NAME = os.getenv('STATUS_NAME', "just vibing")
FIRESTORE_PROJECT_ID = os.getenv('FIRESTORE_PROJECT_ID')
FIRESTORE_COLLECTION = os.getenv('FIRESTORE_COLLECTION', 'user_audio')
MAX_INTRO_CLIP_SECONDS = float(os.getenv('MAX_INTRO_CLIP_SECONDS', '5'))
MAX_NUM_CLIPS = int(os.getenv('MAX_NUM_CLIPS', '10'))


# TODO implement bot commands
# global discord objects
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot('!', intents=intents)


def setup_logging():
    # use default discord logger
    discord.utils.setup_logging(level=logging.INFO)


class AudioCog(commands.Cog):
    def __init__(self, bot: commands.Bot, data_bucket: str, firestore_project_id: str, firestore_collection: str, tmp_cache: str ='./data/cache'):
        # tmp dirs don't work with FFmpeg for some reason... need to manage ourselves
        self.tmp_cache_dir = tmp_cache
        self.firestore_project_id = firestore_project_id
        self.firestore_collection = firestore_collection
        self.data_bucket = data_bucket
        self._storage_client = None
        self._firestore_client = None
        self.col_ref = self.firestore_client.collection(firestore_collection)
        self.bot = bot
        
        os.makedirs(self.tmp_cache_dir, exist_ok=True)

    @property
    def storage_client(self):
        if not self._storage_client:
            self._storage_client = Storage()
        return self._storage_client

    @property
    def firestore_client(self):
        if not self._firestore_client:
            self._firestore_client = firestore.AsyncClient(project=self.firestore_project_id)
        return self._firestore_client
    
    @app_commands.command()
    async def list_clips(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_clip = await self.get_equipped_clip(user_id)
        all_clips = await self.get_all_clips(user_id)

        msg = ""

        if current_clip:
            msg = f"Equipped clip: {current_clip}"

        if all_clips:
            msg += f"\n\n Saved clips:"
            for clip in all_clips:
                msg += f"\n\t - {clip.get('clip_name')}"

        if not msg:
            msg = "Can't find your clips... did you set any with /add_intro_clip?"
        
        await interaction.response.send_message(msg)
    
    async def get_equipped_clip(self, user_id: str):
        document_ref = self.col_ref.document(user_id)
        doc = await document_ref.get(['clip_name'])
        clip_name = doc.to_dict().get('clip_name')
        return clip_name

    async def get_all_clips(self, user_id: str):
        document_ref = self.col_ref.document(user_id)
        doc = await document_ref.get(['audio_clips'])
        if doc.exists:
            audio_clips = doc.to_dict().get('audio_clips', [])
        else:
            audio_clips = []
        return audio_clips

    @app_commands.command()
    async def play_clip(self, interaction: discord.Interaction, clip_name: str):
        user_id = str(interaction.user.id)
        audio_clips = await self.get_all_clips(user_id)
        content_uri = ""
        for audio_clip in audio_clips:
            if audio_clip.get("clip_name") == clip_name:
                content_uri = audio_clip.get("content_uri")
        
        if not content_uri:
            return await interaction.response.send_message("You need to /add_intro_clip before playing it!")

        vc = get(self.bot.voice_clients, guild=interaction.guild)
        if not vc:
            return await interaction.response.send_message("Connect the bot to a voice channel before playing your clip!")
        
        await interaction.response.send_message("Playing your clip!")
        await self._play_content(vc, content_uri)
    


    @app_commands.command()
    async def join_voice_channel(self, interaction: discord.Interaction, channel: str):
        for voice_channel in interaction.guild.voice_channels:
            if channel == voice_channel.name:
                break
        
        await voice_channel.connect()

        await interaction.response.send_message(f"Connected to {channel}!")


    @join_voice_channel.autocomplete('channel')
    async def channel_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        channels = interaction.guild.voice_channels
        return [
            app_commands.Choice(name=channel.name, value=channel.name)
            for channel in channels if current.lower() in channel.name.lower()
        ]


    @app_commands.command()
    async def disconnect_from_voice(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client is not None:
            voice_channel_name = voice_client.channel.name
            await voice_client.disconnect()
            await interaction.response.send_message(f"Disconnected from {voice_channel_name}!")
        else:
            await interaction.response.send_message("Not connected to any channels in this server!")


    @app_commands.command()
    async def add_intro_clip(self, interaction: discord.Interaction, clip_name: str, youtube_link: str, start_time: str, end_time: str):
        # TODO: logic for downloading via youtube_dl and storing in db
        # should be unique user + clip_name
        user_id = str(interaction.user.id)
        audio_clips = await self.get_all_clips(user_id)

        if audio_clips:
            ok, msg = await self.clip_add_ok(audio_clips, clip_name)
            if not ok:
                await interaction.response.send_message(msg)
                return

        ok, msg = await self.time_ok(float(start_time), float(end_time))

        if not ok:
            await interaction.response.send_message(msg)
            return
        
        await interaction.response.send_message(f"Adding and setting your new clip to be active!")
        
        await self.process_user_clip(str(interaction.user.id), youtube_link, float(start_time), float(end_time), clip_name)

        logging.info(f"done adding clip {clip_name}")
    
    async def time_ok(self, start_time: float, end_time: float) -> Tuple[bool, str]:
        if end_time - start_time > MAX_INTRO_CLIP_SECONDS:
            return False, f"Clip length is greater than max time of {MAX_INTRO_CLIP_SECONDS} seconds"
        return True, ""

    async def clip_add_ok(self, audio_clips: str, clip_name: str):
        if len(audio_clips) >= MAX_NUM_CLIPS:
            clip_names = [clip.get("clip_name") for clip in audio_clips]
            if clip_name not in clip_names:
                return False, f"you've added too many clips! override an existing clip name, or use the /remove_clip command to free up space"
        
        return True, ""

    @app_commands.command()
    async def choose_intro_clip(self, interaction: discord.Interaction, clip_name: str):
        user_id = str(interaction.user.id)
        audio_clips = await self.get_all_clips(user_id)
        data = {}
        for clip in audio_clips:
            if clip.get('clip_name') == clip_name:
                data = clip
        
        if data:
            await self.col_ref.document(user_id).set(data, merge=True)
            await interaction.response.send_message(f"Your intro clip is now {clip_name}")
        
        else:
            await interaction.response.send_message(f"Something went wrong... couldn't set your clip :(")

    @app_commands.command()
    async def delete_clip(self, interaction: discord.Interaction, clip_name: str):
        user_id = str(interaction.user.id)
        equipped_clip_name = await self.get_equipped_clip(user_id)
        if clip_name == equipped_clip_name:
            await interaction.response.send_message(f"Can't remove currently equipped clip...")
            return
        
        audio_clips = await self.get_all_clips(user_id)
        idx_to_delete = None
        for i, clip in enumerate(audio_clips):
            if clip.get('clip_name') == clip_name:
                idx_to_delete = i
                break
        
        if idx_to_delete is not None:
            audio_clips.pop(i)
            await self.col_ref.document(user_id).set({"audio_clips": audio_clips}, merge=True)
            await interaction.response.send_message(f"Clip {clip_name} deleted!")
            
        else:
            await interaction.response.send_message(f"Something went wrong... couldn't set your clip :(")


    @choose_intro_clip.autocomplete("clip_name")
    @play_clip.autocomplete("clip_name")
    @delete_clip.autocomplete("clip_name")
    async def clip_name_autocomplete(self, interaction: discord.Interaction, current: str):
        # TODO: get clip names from db
        user_id = str(interaction.user.id)
        
        all_clip_names = [clip.get('clip_name') for clip in await self.get_all_clips(user_id)]
        
        return [
            app_commands.Choice(name=clip_name, value=clip_name) 
            for clip_name in all_clip_names if current.lower() in clip_name.lower() 
        ]

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.id == self.bot.user.id:
            return
        
        if before.channel == after.channel:
            logging.warning("before and after channels the same - something is wrong")
            return


        for voice_client in self.bot.voice_clients:
            # when we hit the channel - process
            if voice_client.channel == after.channel:
                if not voice_client.is_connected():
                    logging.info('voice_client not connected, connecting!')
                    voice_client = await voice_client.channel.connect()

                logging.info(f"Playing intro clip for user {member.name} in channel {after.channel.name}")
                
                doc_ref = self.col_ref.document(str(member.id))

                doc = await doc_ref.get(['content_uri'])
                content_uri = doc.to_dict().get('content_uri')
                if content_uri is None:
                    return
                
                await self._play_content(voice_client, content_uri)
                
                return


    async def _play_content(self, vc: discord.VoiceClient, content_uri: str):
        # have to handle files this way due to async ffmpeg call
        fname = os.path.join(self.tmp_cache_dir, str(uuid4()))
        await self.storage_client.download_to_filename(self.data_bucket, content_uri.split(self.data_bucket)[-1][1:], fname)

        audio_source = discord.FFmpegOpusAudio(fname)
        if not vc.is_playing():
            vc.play(audio_source)
        else:
            logging.warning(f"can't play audio since audio is already playing")
        
        # wait until voice is played before deleting the file
        if os.path.exists(fname):
            await asyncio.sleep(2*MAX_INTRO_CLIP_SECONDS)
            os.remove(fname)

    async def process_user_clip(self, member_id: str, url: str, start_time: int, end_time: int, clip_name: str):
        logging.info(f"processing audio clip from url: {url}")
        with TemporaryDirectory() as tempdirname:
            mp3_path = download_and_process_clip(url, start_time, end_time, download_path=tempdirname)

            gcs_name = os.path.join(member_id, f'{clip_name}.mp3')
            
            # for now we store in gcs and firestore
            logging.info("uploading audio clip to gcs")
            await self.storage_client.upload_from_filename(self.data_bucket, gcs_name, mp3_path)

            logging.info("updating db")
            await self.update_user_audio(member_id, clip_name, f"gs://{self.data_bucket}/{gcs_name}")


    async def update_user_audio(self, member_id: str, clip_name: str, content_uri: str):
        doc_ref = self.col_ref.document(member_id)
        document = await doc_ref.get(['audio_clips'])
        audio_clips = document.to_dict().get('audio_clips')
        
        data = {
            "clip_name": clip_name,
            "content_uri": content_uri,
        }
        
        if audio_clips is not None:
            logging.info("audio clips found, updating array")

            this_clip = [{"clip_name": clip_name, "content_uri": content_uri}]
            clips_to_keep = [clip for clip in audio_clips if clip.get('clip_name') != clip_name]
            
            clips_to_write = this_clip + clips_to_keep
            
            data['audio_clips'] = clips_to_write

        else:
            logging.info("no audio clips found, creating new record")  
            data['audio_clips']= [
                {"clip_name": clip_name, "content_uri": content_uri}
            ]
        
        await doc_ref.set(data, merge=True)


@bot.listen()
async def on_ready():
    setup_logging()
    
    # check we can play audio
    try:
        discord.opus.load_opus(ctypes.util.find_library('opus'))
    except:
        logging.exception("something went wrong loading opus...")
    
    logging.info("Opus status: {}".format(discord.opus.is_loaded()))

    # sync command tree
    await bot.add_cog(AudioCog(bot, DATA_BUCKET, FIRESTORE_PROJECT_ID, FIRESTORE_COLLECTION), override=True)
    await bot.tree.sync()

    # TODO: initialize db and instantiate connection
    
    logging.info("The bot is ready!")
    
    # go online
    await bot.change_presence(status=discord.Status.online,
                                 activity=discord.Game(name=STATUS_NAME))


if __name__ == "__main__":

    bot.run(BOT_TOKEN)
