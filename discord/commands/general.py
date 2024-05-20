import random
from discord import Colour, Embed, Message
from typing import List

from . import Command

import common.servers as servers

class WhatIfCommand(Command):
    
    def __init__(self) -> None:
        super().__init__("whatif", "Shows how much pp you would gain for a single or multiple plays")
    
    async def run(self, message: Message, args: List[str]):
        parsed = self._parse_args(args)
        server = None
        username = 0
        mode = 0
        relax = 0
        to_add = []

        if 'formatting' in parsed:
            formatting = parsed['formatting']
        if parsed['default']:
            if parsed['default'][0].isdigit():
                to_add = [int(x) for x in parsed['default']]
            else:
                username = parsed['default'][0]
                to_add = [int(x) for x in parsed['default'][1:]]
        else:
            await message.reply("Specify a number.")
            return

        if 'server' in parsed:
            server = servers.by_name(parsed['server'])
            if not server:
                await message.reply(f"Unknown server! Use !servers to see available servers.")
                return

        if 'mode' in parsed:
            mode = parsed['mode'][0]
            relax = parsed['mode'][1]

        link = self._get_link(message)
        if link:
            if not server:
                server = servers.by_name(link.default_server)
            if not username:
                username = link.links[server.server_name]
            if not 'mode' in parsed:
                mode = link.default_mode
                relax = link.default_relax
        elif not username:
            await self._msg_not_linked(message)
            return

        if not server:
            server = servers.by_name("akatsuki")

        user, stats = server.get_user_info(username, mode, relax)

        if not user:
            await message.reply(f"User not found on {server.server_name}!")
            return

        top_plays = server.get_user_best(user.id, mode, relax)
        
        if not top_plays:
            await message.reply(f"No plays found on {server.server_name}!")
            return
        
        top_plays = [x.pp for x in top_plays]
        
        total_pp = 0
        
        for x in range(min(len(top_plays), 100)):
            total_pp += top_plays[x] * 0.95 ** x
        
        bonus_pp = stats[0].pp - total_pp
        print(stats[0].pp, total_pp, bonus_pp)
        percentage_filled = (min(bonus_pp, 416.32) / 416.32) * 100

        if len(to_add) == 1:
            top_plays.append(to_add[0])
        else:
            for i in range(0, len(to_add), 2):
                stuff = to_add[i:i+2]
                if len(stuff) == 1:
                    top_plays.append(stuff[0])
                else:
                    top_plays.extend([stuff[1] for x in range(stuff[0])])
        
        top_plays.sort(reverse=True)
        
        recalced = 0
        
        for x in range(min(len(top_plays), 100)):
            recalced += top_plays[x] * 0.95 ** x
        
        recalced += bonus_pp
        
        if recalced == stats[0].pp:
            await message.reply("You wouldn't gain pp.")
            return
        
        embed = Embed()
        embed.description = ""

        if len(to_add) == 1:
            embed.title = f"What if {user.username} set a {to_add[0]}pp play?"
            for x in range(min(len(top_plays), 100)):
                if top_plays[x] == to_add[0]:
                    embed.description = f"It would be their #{x+1} top play.\n"
        else:
            embed.title = f"What if {user.username} set a lot of plays?"

        embed.description += f"They would gain about **{recalced - stats[0].pp:.2f}pp**\ntotal pp would become **{recalced:,.2f}pp**."
        embed.set_thumbnail(url=f"{server.get_user_pfp(user.id)}?cachemakesmesad={random.randint(0, 9**9)}")
        embed.set_footer(text=f"Bonus PP status: {percentage_filled:.0f}%")
        embed.colour = Colour(int(recalced))
        await message.reply(embed=embed)