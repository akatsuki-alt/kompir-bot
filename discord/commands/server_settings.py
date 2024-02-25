from common.database.objects import DBServerPreferences
from discord import Message
from typing import List
from . import Command

import common.app as app
class SetPrefixCommand(Command):
    
    def __init__(self) -> None:
        super().__init__("setprefix", "Set bot prefix")
        
    async def run(self, message: Message, args: List[str]):
        if not args:
            await message.reply("Usage: !setprefix <prefix>")
            return
        has_role = False
        for role in message.author.roles:
            if role.permissions.administrator or role.permissions.manage_guild:
                has_role = True
                break
        if not has_role:
            await message.reply("You don't have permission to use this command!")
            return
        with app.database.managed_session() as session:
            if (guild := session.get(DBServerPreferences, message.guild.id)):
                guild.prefix = args[0]
                session.commit()
            else:
                session.add(DBServerPreferences(guild_id=message.guild.id, prefix=args[0]))
                session.commit()
        await message.reply(f"Set prefix to {args[0]}.")