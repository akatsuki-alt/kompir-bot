from common.api.server_api import User, Stats, ServerAPI
from common.database.objects import DBStatsTemp, DBStats
from common.app import database
from . import Command

from datetime import datetime, timedelta
from discord import Embed, Message
from typing import List

import common.servers as servers
import random

def format_level(level: float) -> str:
    return f"{level:.0f} +{(level - int(level))*100:.1f}%"

def format_playtime(playtime: int) -> str:
    if playtime > 3600:
        return f"{playtime // 3600}h {playtime % 3600 // 60}m"
    else:
        return f"{playtime // 60}m {playtime % 60}s"

class ShowCommand(Command):
    
    variable_names = {
        'ranked_score': 'Ranked Score',
        'total_score': 'Total Score',
        'play_count': 'Play Count',
        'play_time': 'Play Time',
        'replays_watched': 'Replays Views',
        'accuracy': 'Accuracy',
        'total_hits': 'Total Hits',
        'max_combo': 'Max Combo',
        'level': 'Level',
        'pp': 'Performance',
        'first_places': 'First Places',
        'global_rank': 'Global Rank',
        'country_rank': 'Country Rank',
        'global_score_rank': 'Global Score Rank',
        'country_score_rank': 'Country Score Rank',
        'xh_rank': 'SS+',
        'x_rank': 'SS',
        'sh_rank': 'S+',
        's_rank': 'S',
        'a_rank': 'A',
        'b_rank': 'B',
        'c_rank': 'C',
        'd_rank': 'D',
        'clears': 'Clears',
        'followers': 'Followers',
        'medals_unlocked': 'Medals Unlocked',
    }
    
    custom_formatting = {
        'level': format_level,
        'play_time': format_playtime
    }
    
    def __init__(self) -> None:
        super().__init__("show", "show info about a player")

    def get_embed(self, server: ServerAPI, user: User, stats: Stats, old_stats: Stats, layout: str) -> Embed:
        embed = Embed(title=f"Stats for {user.username}")
        embed.set_thumbnail(url=f"{server.get_user_pfp(user.id)}?cachemakesmesad={random.randint(0, 9**9)}")
        fields = [x.split("|") for x in layout.split("/")]
        for field in fields:
            name = field[0]
            formatting = "{:.2f}"
            reverse = False
            if len(field) > 1:
                formatting = field[1]
                if len(field) > 2:
                    reverse = bool(field[2])
            def format(value: float) -> str:
                if formatting in self.custom_formatting:
                    return self.custom_formatting[formatting](value)
                else:
                    return formatting.format(value)
            if name in stats.__dict__:
                value = format(getattr(stats, name))
                suffix = ""
                if old_stats and name in old_stats.__dict__ and old_stats.__dict__[name]:
                    difference = getattr(stats, name) - getattr(old_stats, name)
                    if reverse:
                        difference = -difference
                    if difference:
                        suffix = f" ({format(difference)})" if difference < 0 else f" (+{format(difference)})"
                embed.add_field(name=self.variable_names[name] if name in self.variable_names else name, value=value+suffix, inline=True)
                    
        return embed

    async def run(self, message: Message, args: List[str]):
        parsed = self._parse_args(args)
        server = None
        username = 0
        mode = 0
        relax = 0
        formatting = "ranked_score|{:,}/total_score|{:,}/total_hits|{:,}/play_count|{:,}/play_time|play_time/replays_watched|{:,}/level|level/accuracy|{:.2f}%/max_combo|{:,}x/global_rank|#{:.0f}/country_rank|#{:.0f}/pp|{:.0f}pp"
        to_compare = None
        if 'compare_to' in parsed:
            to_compare = datetime.strptime(parsed['compare_to'], '%d/%m/%Y').date()
        if 'formatting' in parsed:
            formatting = parsed['formatting']
        if parsed['default']:
            username = parsed['default'][0]
        if 'server' in parsed:
            server = servers.by_name(parsed['server'])
            if not server:
                await message.reply(f"Unknown server! Use !servers to see available servers.")
                return
        if 'mode' in parsed:
            m = self._get_mode_from_string(parsed['mode'])
            if not m:
                await message.reply(f"Unknown mode!")
                return
            mode = m[0]
            relax = m[1]
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
        if not server.supports_rx:
            relax = 0
        stats = stats[0].to_db()
        old_stats = None
        with database.managed_session() as session:
            for stat in session.query(DBStatsTemp).filter(
                DBStatsTemp.server == server.server_name,
                DBStatsTemp.user_id == user.id,
                DBStatsTemp.mode == mode,
                DBStatsTemp.relax == relax,
                DBStatsTemp.discord_id == message.author.id
            ).order_by(DBStatsTemp.date.asc()):
                if (datetime.now() - stat.date) > timedelta(days=1):
                    session.delete(stat)
                elif not old_stats:
                    old_stats = stat
                    session.expunge(stat)
            if old_stats:
                if (datetime.now() - old_stats.date) > timedelta(minutes=5):
                    session.merge(stats.copy(message.author.id))
            else:
                session.merge(stats.copy(message.author.id))
            if to_compare:
                old_stats = session.get(DBStats, (server.server_name, user.id, mode, relax, to_compare))
                if not old_stats:
                    await message.reply(f"We don't have stats stored for that day...")
                    return
                session.expunge(old_stats)
            session.commit()
        await message.reply(embed=self.get_embed(server, user, stats, old_stats, formatting))
