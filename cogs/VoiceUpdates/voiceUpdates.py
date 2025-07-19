import disnake
from disnake.ext import commands

import i18n

from main import CloneVoiceBot
from db.db import Database

class VoiceUpdates(commands.Cog):
    def __init__(self, bot: CloneVoiceBot, db: Database):
        self.bot = bot
        self.db = db

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if (after.channel):
            parent_result = self.db.get_parent_voice(after.channel.id)
            if (parent_result and before.channel != after.channel):
                category = after.channel.category
                overwrites = after.channel.overwrites

                template: str = parent_result["name_template"]
                serial = self.db.get_next_serial_number(after.channel.id)

                name = template.replace("{user}", member.nick or member.global_name).replace("{serial}", str(serial))

                cloned_channel = await after.channel.guild.create_voice_channel(
                    name=name,
                    category=category,
                    overwrites=overwrites,
                    bitrate=after.channel.bitrate,
                    user_limit=after.channel.user_limit
                )

                self.db.add_temporary_voice(cloned_channel.id, after.channel.id, after.channel.guild.id, serial)

                await member.move_to(cloned_channel)
        if (before.channel):
            temp_voice_result = self.db.get_temporary_voice(before.channel.id)
            if (not temp_voice_result):
                # Ignoring voice event completely
                return
            if (len(before.channel.members) == 0):
                self.db.delete_temporary_voice(before.channel.id)
                await before.channel.delete(reason=i18n.t("voice_updates.voice_is_empty"))
                return
        

def setup(bot: CloneVoiceBot):
    from main import db
    bot.add_cog(VoiceUpdates(bot, db))
