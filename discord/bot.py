from bot.discord.commands.ping import PingCommand

from bot.discord.commands import Command
from common.logging import get_logger
from common.service import Service
from common.app import config
from discord import Client
from typing import List

import discord

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
        # TODO: custom prefixes
        prefix = "!"
        if message.content.startswith("!"):
            split = message.content.split(" ")
            command = split[0][len(prefix):]
            args = split[1:]
            for cmd in self.commands:
                if cmd.name == command or command in cmd.aliases:
                    self.logger.info(f"{message.author.name} ({message.author.id}): {message.content}")
                    await cmd.run(message, args)
                    return
            await message.reply("Unknown command!")
    
    def get_commands(self) -> List[Command]:
        return [PingCommand()]

class DiscordBotService(Service):
    def __init__(self):
        super().__init__("discord_bot", daemonize=True)

    def run(self):
        bot = DiscordBot()
        bot.run(config.discord_token)