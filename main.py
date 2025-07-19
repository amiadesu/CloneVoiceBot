import disnake
from disnake.ext import commands
import asyncio
import os

from dotenv import load_dotenv

from db.db import Database

from _i18n.config import setup_i18n

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DB_URL = os.getenv("DB_URL")
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE")
GUILD_ID = int(os.getenv("GUILD_ID"))

setup_i18n(default_locale = DEFAULT_LOCALE)

db = Database(DB_URL)

class CloneVoiceBot(commands.InteractionBot):
    def __init__(self):
        intents = disnake.Intents.default()
        super().__init__(intents=intents)

        self.help_command_color = disnake.Color.blurple()
        self.registration_embed_color = disnake.Color.purple()

        self.load_all_cogs()

    async def on_ready(self):
        print(f"Bot is online as {self.user}")

    def load_all_cogs(self):
        self.load_extension("cogs.Help.help")
        self.load_extension("cogs.Registration.registration")
        self.load_extension("cogs.VoiceUpdates.voiceUpdates")
    
    def check_guild(self, guild_id: int):
        return (guild_id == GUILD_ID) # Ignore all interactions that are not from whitelisted guild

    def get_channel_mention(self, channel_id: int) -> str:
        """Returns command mention string for a channel with given id."""
        return f"<#{channel_id}>"

    def get_command_mention(self, command_name: str) -> str:
        """Returns command mention string for a command with given name if command exists, otherwise returns empty string."""
        command = self.get_global_command_named(command_name)
        if (command is None):
            return ""
        return f"</{command.name}:{command.id}>"

async def main():
    bot = CloneVoiceBot()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())