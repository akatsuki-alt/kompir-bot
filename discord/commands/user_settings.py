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
                link.permissions = 0
                link.links = {}
                link.preferences = {}
                session.add(link)
            link.links[server_name] = user.id
            flag_modified(link, 'links')
            flag_modified(link, 'preferences')
            session.commit()
        
        await message.reply(f"Linked {user.username} ({user.id}) on {server_name}!")

class SetDefaultModeCommand(Command):
    
    def __init__(self):
        super().__init__("defaultmode", "Set default mode")
    
    async def run(self, message: Message, args: List[str]):
        if len(args) != 1:
            await message.reply("Usage: !defaultmode <mode>")
            return
        if not (link := self._get_link(message)):
            await self._msg_not_linked(message)
            return        
        if not (mode := self._get_mode_from_string(args[0])):
            modes = ", ".join([key for key in self._get_modes().keys()])
            await message.reply(f"Unknown mode! Available modes: \n```\n{modes}```")
            return
        link.default_mode = mode[0]
        link.default_relax = mode[1]
        with database.session as session:
            session.merge(link)
            session.commit()
        await message.reply(f"Set default mode to {args[0]}!")

class SetDefaultServerCommand(Command):
    
    def __init__(self):
        super().__init__("defaultserver", "Set default server")
    
    async def run(self, message: Message, args: List[str]):
        if len(args) != 1:
            await message.reply("Usage: !defaultserver <server>")
            return
        if not (link := self._get_link(message)):
            await self._msg_not_linked(message)
            return
        if not servers.by_name(args[0]):
            await message.reply(f"Unknown server: {args[0]}! Use !servers to see available servers.")
            return
        if args[0] not in link.links:
            await message.reply(f"You are not linked on {args[0]}!")
            return
        link.default_server = args[0]
        with database.session as session:
            session.merge(link)
            session.commit()
        await message.reply(f"Set default server to {args[0]}!")