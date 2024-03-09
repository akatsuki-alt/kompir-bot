from discord import ButtonStyle, Interaction, Message, Embed
from discord.ui import View, button, Button

from datetime import datetime, timedelta, date

from wrapper.akatsuki_alt_api.api import instance as api
from common.database.objects import DBStats, DBStatsTemp
from common.constants import Mods

from typing import List
from . import Command

import common.repos.beatmaps as beatmaps
import common.servers as servers
import common.app as app
import random

class ShowCommand(Command):
    
    def __init__(self):
        super().__init__("show", "Shows an osu session progress")

    def get_current_stats(self, server: str, user_id: int, mode: int, relax: int, discord_id: int) -> DBStatsTemp | None:
        _, stats = servers.by_name(server).get_user_info(user_id)
        for stat in stats:
            if stat.mode == mode and stat.relax == relax:
                return stat.to_db().copy(discord_id)
        return None

    def get_last_stats(self, server: str, user_id: int, mode: int, relax: int, discord_id: int) -> DBStatsTemp:
        yesterday = datetime.now() - timedelta(days=1)
        with app.database.managed_session() as session:
            for stats in session.query(DBStatsTemp).filter(DBStatsTemp.date < yesterday):
                session.delete(stats)
                session.commit()
            recorded_stats = session.query(DBStatsTemp).filter(
                DBStatsTemp.user_id == user_id,
                DBStatsTemp.server == server,
                DBStatsTemp.mode == mode,
                DBStatsTemp.relax == relax
            ).order_by(DBStatsTemp.date.asc())
            if recorded_stats.count() == 0:
                stats = self.get_current_stats(server, user_id, mode, relax, discord_id)
                session.merge(stats)
                session.commit()
            else:
                stats = recorded_stats.first()
        return stats

    def get_stats_for_date(self, server: str, user_id: int, mode: int, relax: int, date: date) -> DBStatsTemp | None:
        with app.database.managed_session() as session:
            if (stats := session.get(DBStats, (server, user_id, mode, relax, date))):
                stats_convert = stats.copy(0)
                stats_convert.date = datetime(date.year, date.month, date.day)
                return stats_convert
    
    async def run(self, message: Message, args: List[str]):
        parsed = self._parse_args(args)
        modes = self._get_modes()

        user = None
        server = None
        mode = -1
        relax = -1
        
        for srv in servers.servers:
            if srv.server_name in parsed:
                server = srv
                break
        for name, (m, r) in modes.items():
            if name in parsed:
                mode = m
                relax = r
                break
        if parsed['default']:
            user = parsed['default'][0]
        
        link = self._get_link(message)
        if not server:
            if not link:
                await self._msg_not_linked(message)
                return
            server = servers.by_name(link.default_server)
        if not user:
            if not link:
                await self._msg_not_linked(message)
                return
            if not server.server_name in link.links:
                await message.reply(f"You are not linked on {server.server_name}!")
                return
            user = link.links[server.server_name]
        if mode == -1:
            if link:
                mode = link.default_mode
                relax = link.default_relax
            else:
                mode = 0
                relax = 0
        if not server.supports_rx:
            relax = 0
        user = server.get_user_info(user)[0]
        if not user:
            await message.reply(f"User not found on {server.server_name}!")
            return
        previous_stats = self.get_last_stats(server.server_name, user.id, mode, relax, message.author.id)
        if 'compare_to' in parsed:
            try:
                date = datetime.strptime(parsed['compare_to'], "%Y-%m-%d")
            except ValueError:
                await message.reply("Invalid date format! Use YYYY-MM-DD!")
                return
            previous_stats = self.get_stats_for_date(server.server_name, user.id, mode, relax, date)
            if not previous_stats:
                await message.reply("No stats found for that date!")
                return
        if datetime.now() - previous_stats.date > timedelta(minutes=5):
            current_stats = self.get_current_stats(server.server_name, user.id, mode, relax, message.author.id)
        else:
            current_stats = previous_stats
        embed = Embed(title=f"Stats for {user.username} on {server.server_name}")
        embed.set_thumbnail(url=f"{server.get_user_pfp(user.id)}?{random.randint(0, 100000000)}")
        
        def add_field(title, name, prefix="", suffix="", format=",", asc=False):
            value = getattr(current_stats, name)
            value_old = getattr(previous_stats, name)
            if value is None or value_old is None:
                 embed.add_field(name=title, value=f"{prefix}{value}{suffix}", inline=True)
            else:
                delta = value_old-value if asc else value-value_old
                delta_str = ""
                if delta:
                    delta_str = f"(+{delta:{format}})" if delta > 0 else f"({delta:{format}})"
                embed.add_field(name=title, value=f"{prefix}{value:{format}}{suffix}\n{delta_str}", inline=True)
        def add_field_level():
            delta = current_stats.level - previous_stats.level
            delta_str = ""
            if delta:
                delta_str = f"(+{delta*100:.2f}%)"
            level = int(current_stats.level)
            percentage = (current_stats.level - level) * 100
            embed.add_field(name="Level", value=f"{level} +{percentage:.2f}% {delta_str}", inline=True)
        def add_field_playtime():
            delta = current_stats.play_time - previous_stats.play_time
            delta_str = ""
            if delta:
                delta_str = f"(+{delta/60:.2f}m)"
            embed.add_field(name="Play time", value=f"{current_stats.play_time/3600:.2f}h {delta_str}", inline=True)
        add_field("Ranked score", "ranked_score")
        add_field("Total score", "total_score")
        add_field("Total hits", "total_hits")
        add_field("Play count", "play_count")
        add_field_playtime()
        add_field("Replays watched", "replays_watched")
        add_field_level()
        add_field("Accuracy", "accuracy", suffix="%", format=".2f")
        add_field("Max combo", "max_combo", suffix="x")
        add_field("Global rank", "global_rank", prefix="#", asc=True)
        add_field("Country rank", "country_rank", prefix="#", asc=True) # TODO: add country
        add_field("Performance points", "pp", suffix="pp", format=".0f")
        add_field("Global score rank", "global_score_rank", prefix="#", asc=True)
        add_field("Country score rank", "country_score_rank", prefix="#", asc=True)
        add_field("First places", "first_places")
        await message.reply(embed=embed)

class ResetCommand(Command):
    
    def __init__(self) -> None:
        super().__init__("reset", "Resets your stats")
    
    async def run(self, message: Message, args: List[str]):
        link = self._get_link(message)
        if not link:
            await self._msg_not_linked(message)
            return
        with app.database.managed_session() as session:
            session.query(DBStatsTemp).filter(DBStatsTemp.discord_id == message.author.id).delete()
            session.commit()
        await message.reply("Stats reset!")

class ClearsView(View):
    
    def __init__(self, title, **api_options):
        super().__init__()
        self.title = title
        self.api_options = api_options
        self.query = api.query_scores(**api_options)
        self.sort_methods = ['pp', 'date', 'score', 'max_combo', 'mods', 'accuracy']
        self.current_sort = 0
        self.desc = True

    def get_embed(self, scores=None) -> Embed:
        if scores is None:
            scores = self.query.next()
        embed = Embed(title=f"{self.title} (Total: {self.query.count}, Page: {self.query._page}/{(self.query.count/7)+1:.0f})")
        for score in scores:
            beatmap = beatmaps.get_beatmap(score.beatmap_id)
            if not beatmap:
                continue
            title = f"**{beatmap.get_title()}**\n"
            desc = f"+{Mods(score.mods).short} {score.rank} {score.max_combo}x {score.accuracy:.2f}% [{score.count_300}/{score.count_100}/{score.count_50}/{score.count_miss}]\n"
            desc += f"Score: {score.score:,} PP: {score.pp:.0f}pp Date: {score.date}\n"
            embed.add_field(name=title, value=desc, inline=False)
        return embed

    @button(label="Previous", style=ButtonStyle.gray)
    async def prev_button(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        await interaction.message.edit(embed=self.get_embed(self.query.prev()), view=self)

    @button(label="Next", style=ButtonStyle.gray)
    async def next_button(self, interaction: Interaction, button: Button):
        if self.query._page >= (self.query.count/7):
            return
        await interaction.response.defer()   
        await interaction.message.edit(embed=self.get_embed(self.query.next()), view=self)
 
    @button(label="Sort: pp", style=ButtonStyle.green)
    async def sort_button(self, interaction: Interaction, button: Button):
        self.current_sort += 1
        if self.current_sort >= len(self.sort_methods):
            self.current_sort = 0
        self.query.set_sort(self.sort_methods[self.current_sort], self.desc)
        button.label = f"Sort: {self.sort_methods[self.current_sort]}"
        await interaction.response.defer()
        await interaction.message.edit(embed=self.get_embed(), view=self)

    @button(label="Order: ↓", style=ButtonStyle.gray)
    async def toggle_desc(self, interaction: Interaction, button: Button):
        await interaction.response.defer()   
        if self.desc:
            self.desc = False
            button.label = "Order: ↑"
        else:
            self.desc = True
            button.label = "Order: ↓"
        self.query.set_sort(self.sort_methods[self.current_sort], self.desc)
        await interaction.message.edit(embed=self.get_embed(), view=self)

    async def reply(self, message: Message):
        await message.reply(embed=self.get_embed(), view=self)

class ShowClearsCommand(Command):
    
    def __init__(self,) -> None:
        super().__init__("showclears", "Shows your clears", aliases=["sc"])
    
    async def run(self, message: Message, args: List[str]):
        parsed = self._parse_args(args)
        modes = self._get_modes()

        user = None
        server = None
        mode = -1
        relax = -1
        
        for srv in servers.servers:
            if srv.server_name in parsed:
                server = srv
                break
        for name, (m, r) in modes.items():
            if name in parsed:
                mode = m
                relax = r
                break
        if parsed['default']:
            user = parsed['default'][0]
        
        link = self._get_link(message)
        if not server:
            if not link:
                await self._msg_not_linked(message)
                return
            server = servers.by_name(link.default_server)
        if not user:
            if not link:
                await self._msg_not_linked(message)
                return
            if not server.server_name in link.links:
                await message.reply(f"You are not linked on {server.server_name}!")
                return
            user = link.links[server.server_name]
        if mode == -1:
            if link:
                mode = link.default_mode
                relax = link.default_relax
            else:
                mode = 0
                relax = 0
        if not server.supports_rx:
            relax = 0
        user = server.get_user_info(user)[0]
        if not user:
            await message.reply(f"User not found on {server.server_name}!")
            return
        query = f"user_id=={user.id},mode=={mode},relax=={relax}"
        await ClearsView(f"{user.username} {self._get_mode_full_name(mode, relax)} Clears", query=query,length=7).reply(message)