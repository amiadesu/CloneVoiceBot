import disnake
from disnake.ext import commands, tasks
from disnake import TextInputStyle
from datetime import datetime, timedelta
from typing import Optional

import i18n

from main import CloneVoiceBot
from db.db import Database

from utils.utils import float_to_str

class Registration(commands.Cog):
    def __init__(self, bot: CloneVoiceBot, db: Database):
        self.bot = bot
        self.db = db

        # Stores message_id: (author_id, expiry_time)
        self.active_interactions = {}
        self.cleanup_task = self.cleanup_expired_interactions.start()

        self.timeout = 4  # in seconds

    def cog_unload(self):
        self.cleanup_task.cancel()

    @tasks.loop(seconds=1)
    async def cleanup_expired_interactions(self):
        """Regularly clean up expired interactions"""
        now = datetime.now()
        to_remove = [
            msg_id
            for msg_id, (_, expiry, _, _) in self.active_interactions.items()
            if expiry < now
        ]

        for msg_id in to_remove:
            await self.disable_message(msg_id)
            del self.active_interactions[msg_id]

    def refresh_interaction_timeout(self, message_id: int):
        """Refresh expiry time of an active interaction."""
        if message_id in self.active_interactions:
            author_id, _, parent_id, name_template = self.active_interactions[message_id]
            new_expiry = datetime.now() + timedelta(seconds=self.timeout)
            self.active_interactions[message_id] = (
                author_id,
                new_expiry,
                parent_id,
                name_template
            )

    async def update_setup_message(
        self,
        message: disnake.Message,
        parent_channel_id: int = None,
        name_template: str = None,
    ):
        """Update the setup message with current settings"""
        if message.id not in self.active_interactions:
            return

        author_id, expiry, current_parent, current_template = self.active_interactions[message.id]

        # Update stored values if new ones provided
        if parent_channel_id is not None:
            current_parent = parent_channel_id
        if name_template is not None:
            current_template = name_template

        # Update the stored data
        self.active_interactions[message.id] = (
            author_id,
            expiry,
            current_parent,
            current_template,
        )

        # Format the display text
        parent_display = (
            i18n.t("registration.not_set")
            if current_parent is None
            else f"<#{current_parent}>"
        )
        template_display = (
            i18n.t("registration.not_set")
            if not current_template
            else f"`{current_template}`"
        )

        # Create updated embed
        embed = disnake.Embed(
            title=i18n.t("registration.embed.title"),
            description=i18n.t("registration.embed.description", minutes=float_to_str(self.timeout / 60)),
            color=self.bot.registration_embed_color,
        )
        embed.add_field(
            name=i18n.t("registration.fields.parent_channel.name"),
            value=parent_display,
            inline=False,
        )
        embed.add_field(
            name=i18n.t("registration.fields.name_template.name"),
            value=template_display,
            inline=False,
        )

        # Keep the same components
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=i18n.t("registration.buttons.parent_channel.label"),
                    custom_id=f"set_parent:{message.id}",
                    style=disnake.ButtonStyle.primary,
                ),
                disnake.ui.Button(
                    label=i18n.t("registration.buttons.name_template.label"),
                    custom_id=f"set_template:{message.id}",
                    style=disnake.ButtonStyle.primary,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=i18n.t("registration.buttons.submit.label"),
                    custom_id=f"submit_parent_channel:{message.id}",
                    style=disnake.ButtonStyle.secondary,
                    disabled=(current_parent is None or not current_template)
                )
            )
        ]

        try:
            await message.edit(embed=embed, components=components)
        except disnake.NotFound:
            pass  # Message was deleted
        except disnake.HTTPException:
            pass  # Other potential errors

    async def disable_message(self, message_id: int):
        """Disable buttons after timeout period"""
        message = self.bot.get_message(message_id)
        if (not message):
            return
        # Edit the message to remove components and update embed
        try:
            embed = message.embeds[0]
            embed.title = i18n.t("registration.embed.title")
            embed.description = i18n.t("registration.interaction_expired")
            await message.edit(embed=embed, components=[])
        except disnake.NotFound:
            pass  # Message was deleted
        except disnake.HTTPException:
            pass  # Other potential errors

    @commands.slash_command(description="Add a new parent voice channel")
    @commands.has_permissions(manage_guild=True)
    async def create_parent_voice(self, inter: disnake.ApplicationCommandInteraction):
        """Main setup command that creates the interactive message"""
        if (not self.bot.check_guild(inter.guild_id)):
            return
        
        embed = disnake.Embed(
            title=i18n.t("registration.embed.title"),
            description=i18n.t("registration.embed.description", minutes=float_to_str(self.timeout / 60)),
            color=self.bot.registration_embed_color,
        )
        embed.add_field(
            name=i18n.t("registration.fields.parent_channel.name"),
            value=i18n.t("registration.not_set"),
            inline=False,
        )
        embed.add_field(
            name=i18n.t("registration.fields.name_template.name"),
            value=i18n.t("registration.not_set"),
            inline=False,
        )

        # Send the message without buttons
        await inter.response.send_message(embed=embed, components=[])

        message = await inter.original_message()

        # Create buttons
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=i18n.t("registration.buttons.parent_channel.label"),
                    custom_id=f"set_parent:{message.id}",
                    style=disnake.ButtonStyle.primary,
                ),
                disnake.ui.Button(
                    label=i18n.t("registration.buttons.name_template.label"),
                    custom_id=f"set_template:{message.id}",
                    style=disnake.ButtonStyle.primary,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=i18n.t("registration.buttons.submit.label"),
                    custom_id=f"submit_parent_channel:{message.id}",
                    style=disnake.ButtonStyle.secondary,
                    disabled=True
                )
            )
        ]

        # Add buttons to message
        await message.edit(embed=embed, components=components)

        # Store the interaction with expiry time and default values
        expiry_time = datetime.now() + timedelta(seconds=self.timeout)
        self.active_interactions[message.id] = (
            inter.author.id,
            expiry_time,
            None,
            None,
        )

    @commands.slash_command(description="Edit an existing parent voice channel or create a new one.")
    @commands.has_permissions(manage_guild=True)
    async def edit_parent_voice(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: Optional[disnake.VoiceChannel] = commands.Param(default=None, description="Parent voice channel to edit (optional)")
    ):
        """Edits an existing parent voice channel, or starts setup if none provided."""
        if (not self.bot.check_guild(inter.guild_id)):
            return

        # If no channel provided, act as alias for create_parent_voice
        if channel is None:
            await self.create_parent_voice(inter)
            return

        # Check if channel is a registered parent voice
        result = self.db.get_parent_voice(channel.id)
        if result is None:
            await inter.response.send_message(
                i18n.t("registration.not_registered"),
                ephemeral=True
            )
            return

        # Begin setup with initial data from DB
        embed = disnake.Embed(
            title=i18n.t("registration.embed.title"),
            description=i18n.t("registration.embed.description", minutes=float_to_str(self.timeout / 60)),
            color=self.bot.registration_embed_color,
        )
        embed.add_field(
            name=i18n.t("registration.fields.parent_channel.name"),
            value=f"<#{result['channel_id']}>",
            inline=False,
        )
        embed.add_field(
            name=i18n.t("registration.fields.name_template.name"),
            value=f"`{result['name_template']}`" if result['name_template'] else i18n.t("registration.not_set"),
            inline=False,
        )

        await inter.response.send_message(embed=embed, components=[])
        message = await inter.original_message()

        # Prepare buttons (not disabled since both values are present)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=i18n.t("registration.buttons.parent_channel.label"),
                    custom_id=f"set_parent:{message.id}",
                    style=disnake.ButtonStyle.primary,
                ),
                disnake.ui.Button(
                    label=i18n.t("registration.buttons.name_template.label"),
                    custom_id=f"set_template:{message.id}",
                    style=disnake.ButtonStyle.primary,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=i18n.t("registration.buttons.submit.label"),
                    custom_id=f"submit_parent_channel:{message.id}",
                    style=disnake.ButtonStyle.secondary,
                    disabled=False
                )
            )
        ]

        await message.edit(embed=embed, components=components)

        # Store interaction with prefilled data
        expiry_time = datetime.now() + timedelta(seconds=self.timeout)
        self.active_interactions[message.id] = (
            inter.author.id,
            expiry_time,
            result['channel_id'],
            result['name_template']
        )

    @commands.slash_command(description="Delete an existing parent voice from database.")
    @commands.has_permissions(manage_guild=True)
    async def delete_parent_voice(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.VoiceChannel = commands.Param(description="Parent voice channel to delete")
    ):
        """Deletes an existing parent voice channel."""
        if (not self.bot.check_guild(inter.guild_id)):
            return
        
        # Check if channel is a registered parent voice
        result = self.db.get_parent_voice(channel.id)
        if result is None:
            await inter.response.send_message(
                i18n.t("registration.not_registered"),
                ephemeral=True
            )
            return

        self.db.delete_parent_voice(channel_id=channel.id)

        await inter.response.send_message(
            i18n.t("registration.submit.delete", channel_mention = channel.mention),
            ephemeral=False
        )
        

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        # Check if this is an active interaction
        if inter.message.id not in self.active_interactions:
            await inter.response.send_message(
                i18n.t("registration.interaction_invalid"), 
                ephemeral=True
            )
            return

        author_id, expiry_time, _, _ = self.active_interactions[inter.message.id]

        # Check if interaction is expired
        if datetime.now() > expiry_time:
            del self.active_interactions[inter.message.id]
            await inter.response.send_message(
                i18n.t("registration.interaction_expired"), 
                ephemeral=True
            )
            return

        # Check if user is authorized
        if inter.author.id != author_id:
            await inter.response.send_message(
                i18n.t("registration.not_author"),
                ephemeral=True,
            )
            return
        
        self.refresh_interaction_timeout(inter.message.id)

        if inter.component.custom_id.startswith("set_parent"):
            await self.handle_parent_channel_selection(inter)
        elif inter.component.custom_id.startswith("set_template"):
            await self.handle_name_template_input(inter)
        elif inter.component.custom_id.startswith("submit_parent_channel"):
            await self.submit_parent_channel(inter)

    async def handle_parent_channel_selection(self, inter: disnake.MessageInteraction):
        """Create a dropdown for voice channel selection"""
        # Get all voice channels in the guild
        voice_channels = [
            channel
            for channel in inter.guild.voice_channels
            if isinstance(channel, disnake.VoiceChannel)
        ]

        if not voice_channels:
            await inter.response.send_message(
                i18n.t("registration.no_voice_channels"), 
                ephemeral=True
            )
            return

        # Create dropdown options
        options = [
            disnake.SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=i18n.t("registration.dropdowns.parent_channel.channel_option_description", channel_id = channel.id),
            )
            for channel in voice_channels
        ]

        (
            author_id,
            expiry,
            parent_id,
            name_template,
        ) = self.active_interactions[inter.message.id]

        if (parent_id):
            for option in options:
                if (option.value == str(parent_id)):
                    option.default = True

        # Create dropdown menu with timeout
        dropdown = disnake.ui.Select(
            placeholder=i18n.t("registration.dropdowns.parent_channel.placeholder"),
            options=options,
            custom_id=f"parent_channel_select:{inter.message.id}",
        )

        view = disnake.ui.View(timeout=self.timeout)
        view.add_item(dropdown)

        await inter.response.send_message(
            i18n.t("registration.dropdowns.parent_channel.message", minutes=float_to_str(self.timeout / 60)),
            view=view,
            ephemeral=True,
        )

    async def handle_name_template_input(self, inter: disnake.MessageInteraction):
        """Create a modal for name template input"""
        (
            author_id,
            expiry,
            parent_id,
            name_template,
        ) = self.active_interactions[inter.message.id]

        default_value = name_template if name_template else ""

        modal = disnake.ui.Modal(
            title=i18n.t("registration.modals.name_template.title"),
            custom_id=f"name_template_modal:{inter.message.id}",
            components=[
                disnake.ui.TextInput(
                    label=i18n.t("registration.modals.name_template.label"),
                    placeholder=i18n.t("registration.modals.name_template.placeholder"),
                    custom_id=f"name_template_input:{inter.message.id}",
                    style=TextInputStyle.short,
                    max_length=100,
                    value=default_value
                )
            ],
        )

        await inter.response.send_modal(modal)

    @commands.Cog.listener()
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        """Handle dropdown selection for parent channel"""
        if inter.data.custom_id.startswith("parent_channel_select"):
            setup_message_id = int(inter.data.custom_id.split(":")[1])

            if setup_message_id not in self.active_interactions:
                await inter.response.send_message(
                    i18n.t("registration.interaction_expired"), ephemeral=True
                )
                return
            
            self.refresh_interaction_timeout(inter.message.id)

            selected_channel_id = int(inter.values[0])
            selected_channel = inter.guild.get_channel(selected_channel_id)

            original_message = await inter.channel.fetch_message(setup_message_id)

            # Update the setup message with new parent channel
            await self.update_setup_message(
                message=original_message, parent_channel_id=selected_channel_id
            )

            await inter.response.send_message(
                i18n.t("registration.parent_channel_change_success", channel_mention = selected_channel.mention),
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        """Handle modal submission for name template"""
        if inter.custom_id.startswith("name_template_modal"):
            setup_message_id = int(inter.data.custom_id.split(":")[1])

            if setup_message_id not in self.active_interactions:
                await inter.response.send_message(
                    i18n.t("registration.interaction_expired"), ephemeral=True
                )
                return
            
            self.refresh_interaction_timeout(inter.message.id)

            name_template = inter.text_values[f"name_template_input:{setup_message_id}"]

            original_message = await inter.channel.fetch_message(setup_message_id)

            # Update the setup message with new template
            await self.update_setup_message(
                message=original_message, name_template=name_template
            )

            await inter.response.send_message(
                i18n.t("registration.name_template_change_success", name_template = name_template),
                ephemeral=True
            )

    async def submit_parent_channel(self, inter: disnake.MessageInteraction):
        (
            author_id,
            expiry,
            parent_id,
            name_template,
        ) = self.active_interactions[inter.message.id]
        
        parent_channel = await self.bot.fetch_channel(parent_id)

        result = self.db.get_parent_voice(parent_id)
        if (result):
            self.db.update_parent_voice(parent_id, inter.guild_id, name_template)
            await inter.response.send_message(
                i18n.t("registration.submit.update", channel_mention = parent_channel.mention),
                ephemeral=False
            )
            return

        self.db.add_parent_voice(parent_id, inter.guild_id, name_template)
        await inter.response.send_message(
            i18n.t("registration.submit.success", channel_mention = parent_channel.mention),
            ephemeral=False
        )


def setup(bot: CloneVoiceBot):
    from main import db

    bot.add_cog(Registration(bot, db))