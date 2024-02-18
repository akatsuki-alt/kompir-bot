from discord import Message
from typing import List
from . import Command

import common.servers as servers

class ServersCommand(Command):
    
    def __init__(self):
        super().__init__("servers", "List supported servers")
    
    async def run(self, message: Message, args: List[str]):
        string = "Available servers: \n```\n"
        for server in servers.servers:
            string += f"{server.server_name}\n\t Supports RX/AP: {server.supports_rx}\n\t Supports Clans: {server.supports_clans}\n\t Supports LB Tracking: {server.supports_lb_tracking}\n"
        string += "```"
        await message.reply(string)