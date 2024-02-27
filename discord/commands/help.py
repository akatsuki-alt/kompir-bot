from discord import Message, Embed
from typing import List
from . import Command

import common.servers as servers
import discord

class Select(discord.ui.Select):
    def __init__(self, callback_function):
        from bot.discord.bot import bot # Avoid circular import...
        self.callback_function = callback_function
        options = list()
        for command in bot.get_commands():
            options.append(discord.SelectOption(label=command.name, description=command.description))
        super().__init__(placeholder="Select an option",max_values=1,min_values=1,options=options)
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.callback_function(self.values[0])

class SelectView(discord.ui.View):
    def __init__(self, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.add_item(Select(self.callback_function))

    async def callback_function(self, command_name):
        from bot.discord.bot import bot # Avoid circular import...
        for command in bot.get_commands():
            if command.name == command_name:
                await self.message.edit(embed=Embed(title=f"{command.name}", description=f"Aliases: {', '.join(command.aliases)}\n{command.description}\n{command.help}"))
                return
    
    async def reply(self, message: Message):
        from bot.discord.bot import bot # Avoid circular import...
        content = ""
        for command in bot.get_commands():
            content += f"{command.name} | {command.description}\n"
        self.message = await message.reply(embed=Embed(title="Help", description=content), view=self)

class HelpCommand(Command):
    
    def __init__(self) -> None:
        super().__init__("help", "show commands", "Select a command to show description!")
    
    async def run(self, message: Message, args: List[str]):
        await SelectView().reply(message)
        return True

class ServersCommand(Command):
    
    def __init__(self):
        super().__init__("servers", "List supported servers")
    
    async def run(self, message: Message, args: List[str]):
        string = "Available servers: \n```\n"
        for server in servers.servers:
            string += f"{server.server_name}\n\t Supports RX/AP: {server.supports_rx}\n\t Supports Clans: {server.supports_clans}\n\t Supports LB Tracking: {server.supports_lb_tracking}\n"
        string += "```"
        await message.reply(string)

