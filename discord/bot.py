from bot.discord.commands.server_settings import SetPrefixCommand
from bot.discord.commands.help import ServersCommand, HelpCommand
from bot.discord.commands.query import DatabaseQueryCommand
from bot.discord.commands.get_file import GetFileCommand
from bot.discord.commands.general import WhatIfCommand
from bot.discord.commands.recent import RecentCommand
from bot.discord.commands.ping import PingCommand
from bot.discord.commands.show import ShowCommand
from bot.discord.commands.user_settings import *
from bot.discord.commands import Command
from common.app import config, database
from common.database.objects import *
from common.logging import get_logger
from common.service import Service
from discord import Client
from typing import List

import discord
import shlex

class DiscordBot(Client):
    
    def __init__(self):
        self.commands = self.get_commands()
        self.logger = get_logger("discord_bot")
        super().__init__(intents=discord.Intents.all())

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return
        prefix = "!"
        with database.managed_session() as session:
            if (preferences := session.get(DBServerPreferences, message.guild.id)):
                prefix = preferences.prefix
        if message.content.startswith(prefix):
            split = shlex.split(message.content)
            command = split[0][len(prefix):]
            args = split[1:]
            for cmd in self.commands:
                if cmd.name == command or command in cmd.aliases:
                    self.logger.info(f"{message.author.name} ({message.author.id}): {message.content}")
                    if cmd.permission_level > 0:
                        link = cmd._get_link(message)
                        if not link:
                            await cmd._msg_no_permission(message)
                            return
                        if link.permissions < cmd.permission_level:
                            await cmd._msg_no_permission(message)
                            return
                    try:
                        await cmd.run(message, args)
                    except Exception as e:
                        error_embed = discord.Embed(title=f"An error has occurred! ({type(e).__name__})")
                        error_embed.description = f"```{e}```"
                        self.logger.error(f"Unhandled exception in command {cmd.name}!", exc_info=e)
                        error_embed.set_footer(text="Error has been reported automatically. No further action is required.")
                        await message.reply(embed=error_embed)
                    return
            await message.reply("Unknown command!")
    
    def get_commands(self) -> List[Command]:
        return [PingCommand(), LinkCommand(), SetDefaultModeCommand(), SetDefaultServerCommand(), RecentCommand(), ServersCommand(), DatabaseQueryCommand(), ShowCommand(), SetPrefixCommand(), HelpCommand(), GetFileCommand(), WhatIfCommand()]

bot: DiscordBot = None

class DiscordBotService(Service):
    def __init__(self):
        super().__init__("discord_bot", daemonize=True)

    def run(self):
        global bot
        bot = DiscordBot()
        bot.run(config.discord_token)