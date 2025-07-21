import disnake
from disnake.ext import commands

import disnake.http
import i18n

from main import CloneVoiceBot
from db.db import Database

class VoiceUpdates(commands.Cog):
    def __init__(self, bot: CloneVoiceBot, db: Database):
        self.bot = bot
        self.db = db

    async def copy_channel_permissions(
        self,
        source_channel_id: int,
        target_channel_id: int
    ):
        """Copy all permission overwrites from one channel to another"""
        # 1. Get permissions from source channel
        get_route = disnake.http.Route(
            'GET',
            '/channels/{channel_id}',
            channel_id=source_channel_id
        )
        
        try:
            channel_data = await self.bot._connection.http.request(get_route)
            overwrites = channel_data.get('permission_overwrites', [])
            
            # 2. Apply to target channel
            put_route = disnake.http.Route(
                'PATCH',
                '/channels/{channel_id}',
                channel_id=target_channel_id
            )
            
            payload = {'permission_overwrites': overwrites}
            await self.bot._connection.http.request(put_route, json=payload)
            return True
        except disnake.HTTPException as e:
            print(f"Error copying channel permissions: {e}")
            return False

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if (after.channel):
            parent_result = self.db.get_parent_voice(after.channel.id)
            if (parent_result and before.channel != after.channel):
                category = after.channel.category

                overwrites = after.channel.overwrites.copy()

                template: str = parent_result["name_template"]
                serial = self.db.get_next_serial_number(after.channel.id)

                name = template.replace("{user}", member.nick or member.global_name or member.name).replace("{serial}", str(serial))

                cloned_channel = await after.channel.guild.create_voice_channel(
                    name=name,
                    category=category,
                    overwrites=overwrites,
                    bitrate=after.channel.bitrate,
                    user_limit=after.channel.user_limit
                )

                # A workaround to disnake's lacking permissions inside overwrites
                await self.copy_channel_permissions(after.channel.id, cloned_channel.id)

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
