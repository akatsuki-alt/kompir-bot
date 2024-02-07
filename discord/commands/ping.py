from discord import Message
from typing import List
from . import Command

class PingCommand(Command):
    
    def __init__(self):
        super().__init__("ping", "Pings the bot.")
        
    async def run(self, message: Message, args: List[str]):
        await message.reply("Pong!")