from sqlalchemy.orm.attributes import flag_modified
from common.database.objects import DBBotLink
from common.app import database
from discord import Message
from typing import List
from . import Command

import common.servers as servers

class LinkCommand(Command):
    
    def __init__(self):
        super().__init__("link", "Link account to bot")
        
    async def run(self, message: Message, args: List[str]):
        if len(args) != 2:
            await message.reply("Usage: !link <username> <server>")
            return
        
        username = args[0]
        server_name = args[1]
        
        if not (server := servers.by_name(server_name)):
            await message.reply(f"Unknown server: {server_name}! Use !servers to see available servers.")
            return
        
        user, _ = server.get_user_info(username)
        
        if not user:
            await message.reply(f"User {username} not found on {server.server_name}!")
            return
        
        with database.session as session:
            if not (link := session.get(DBBotLink, message.author.id)):
                link = DBBotLink(discord_id=message.author.id)
                link.default_server = server_name
                link.default_mode = 0
                link.default_relax = 0
                link.links = {}
                link.preferences = {}
                session.add(link)
            link.links[server_name] = user.id
            flag_modified(link, 'links')
            flag_modified(link, 'preferences')
            session.commit()
        
        await message.reply(f"Linked {user.username} ({user.id}) on {server_name}!")
