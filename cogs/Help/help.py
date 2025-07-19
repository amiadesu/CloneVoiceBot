import disnake
from disnake.ext import commands
import io

import i18n

from main import CloneVoiceBot
from db.db import Database

class Help(commands.Cog):
    def __init__(self, bot: CloneVoiceBot, db: Database):
        self.bot = bot
        self.db = db

    @commands.slash_command(name="help", description="Show available commands and bot's description.")
    async def help_command(self, inter: disnake.ApplicationCommandInteraction):
        if (not self.bot.check_guild(inter.guild_id)):
            return
        
        embed = disnake.Embed(
            title=i18n.t("help.title"),
            description = 
                i18n.t("help.description.bot")
                + i18n.t("help.description.parent_channels")
                + i18n.t("help.description.name_template")
                + i18n.t("help.description.commands"),
            color=self.bot.help_command_color
        )

        embed.add_field(
            name=i18n.t("help.fields.help.name"), 
            value=i18n.t(
                "help.fields.help.value", 
                command_mention = self.bot.get_command_mention("help")
            ), 
            inline=True
        )
        embed.add_field(
            name=i18n.t("help.fields.create_parent_voice.name"), 
            value=i18n.t(
                "help.fields.create_parent_voice.value", 
                command_mention = self.bot.get_command_mention("create_parent_voice")
            ), 
            inline=True
        )
        embed.add_field(
            name=i18n.t("help.fields.edit_parent_voice.name"), 
            value=i18n.t(
                "help.fields.edit_parent_voice.value", 
                command_mention = self.bot.get_command_mention("edit_parent_voice")
            ), 
            inline=True
        )
        embed.add_field(
            name=i18n.t("help.fields.delete_parent_voice.name"), 
            value=i18n.t(
                "help.fields.delete_parent_voice.value", 
                command_mention = self.bot.get_command_mention("delete_parent_voice")
            ), 
            inline=True
        )
        embed.add_field(
            name=i18n.t("help.fields.parent_channels_list.name"), 
            value=i18n.t(
                "help.fields.parent_channels_list.value", 
                command_mention = self.bot.get_command_mention("parent_channels_list")
            ), 
            inline=True
        )

        await inter.response.send_message(embed=embed, ephemeral=False)

    @commands.slash_command(name="parent_channels_list", description="Shows all parent channels that are present in this guild.")
    async def parent_channels_list(self, inter: disnake.ApplicationCommandInteraction):
        if (not self.bot.check_guild(inter.guild_id)):
            return
        
        all_parent_channels = self.db.get_all_parent_voices_from_guild(inter.guild_id)
        description = ""
        if (len(all_parent_channels) == 0):
            description = i18n.t("parent_channels_list.no_channels")
        else:
            for data in all_parent_channels:
                channel_id = data["channel_id"]
                name_template = data["name_template"]
                channel_mention = self.bot.get_channel_mention(channel_id)
                description += i18n.t(
                    "parent_channels_list.row_template",
                    channel_mention = channel_mention,
                    name_template = name_template
                )
        if (len(description) < 4096): # Discord's description length limit
            embed = disnake.Embed(
                title=i18n.t("parent_channels_list.title"),
                description = description,
                color=self.bot.help_command_color
            )

            await inter.response.send_message(embed=embed, ephemeral=False)
        else:
            file_content = io.StringIO(i18n.t("parent_channels_list.title") + description)
            file_content.seek(0)

            # Send the file back to the user
            await inter.response.send_message(
                file=disnake.File(file_content, filename="parent_channels_list.txt")
            )

def setup(bot: CloneVoiceBot):
    from main import db
    bot.add_cog(Help(bot, db))
