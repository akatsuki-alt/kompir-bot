import discord
from common.database.objects import DBStatsTemp, DBStats, DBUser, DBScore
from common.api.server_api import User, Stats, ServerAPI
from common.app import database
from . import Command

from datetime import datetime, timedelta
from discord.ui import View, button
from common.constants import Mods
from discord import Color, Colour, Embed, Message
from typing import List
from common.repos import beatmaps
import common.servers as servers
import random
from common.performance import by_version, SimulatedScore

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
        embed.color = Colour(user.id if user.id < 16777215 else int(user.id / 9**3))
        
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
                attr = getattr(stats, name)
                value = format(attr) if attr is not None else "N/A"
                suffix = ""
                if old_stats and name in old_stats.__dict__ and old_stats.__dict__[name]:
                    difference = getattr(stats, name) - getattr(old_stats, name)
                    if reverse:
                        difference = -difference
                    if difference: # Stats have changed thus showing gain/loss
                        suffix = f" ({format(difference)})" if difference < 0 else f" (+{format(difference)})"
                embed.add_field(name=self.variable_names[name] if name in self.variable_names else name, value=value+suffix, inline=True)
        
        return embed

    async def run(self, message: Message, args: List[str]):
        parsed = self._parse_args(args)
        server = None
        username = 0
        mode = 0
        relax = 0
        # Default formatting, format is field_name|formatting|use reverse gain (boolean)/....
        # TODO: Get formatting from user's config
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

        if not server.supports_rx: # Fixes nasty side effect of saving stats as rx
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
            ).order_by(DBStatsTemp.date.asc()): # Find oldest stats that isnt expired
                if (datetime.now() - stat.date) > timedelta(days=1):
                    session.delete(stat)
                elif not old_stats:
                    old_stats = stat
                    session.expunge(stat)
            
            if old_stats: # Save stats if more than 10 minutes elapsed
                if (datetime.now() - old_stats.date) > timedelta(minutes=10):
                    session.merge(stats.copy(message.author.id))
            else:
                session.merge(stats.copy(message.author.id))

            if to_compare: # Get stats from db if a date is specified
                old_stats = session.get(DBStats, (server.server_name, user.id, mode, relax, to_compare))
                if not old_stats:
                    await message.reply(f"We don't have stats stored for that day...")
                    return
                session.expunge(old_stats)
            session.commit()

        await message.reply(embed=self.get_embed(server, user, stats, old_stats, formatting))

class TopView(View):
    
    def __init__(self, user: DBUser, mode: int, relax: int, query):
        super().__init__()
        self.sort_methods = [
            ("pp", "PP"),
            ("date", "Date"),
            ("accuracy", "Accuracy"),
            ("score", "Score"),
            ("max_combo", "Max Combo"),
        ]
        self.user = user
        self.length = 5
        self.count = query.count()
        self.page = 0
        self.sort = 0
        self.desc = True
        self.mode = mode
        self.relax = relax
        self.query = query
        self.actual_query = self.query.order_by(getattr(DBScore, self.sort_methods[self.sort][0]).desc())  
      
    @button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.count/self.length-1:
            self.page += 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @button(label="Last", style=discord.ButtonStyle.secondary)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        if button.label == "Last":
            self.page = int(self.count/self.length)-1
            button.label = "First"
        else:
            self.page = 0
            button.label = "Last"
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @button(label="PP", style=discord.ButtonStyle.secondary)
    async def sort(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.sort += 1
        if self.sort >= len(self.sort_methods):
            self.sort = 0
        button.label = self.sort_methods[self.sort][1]
        if self.desc: # lazy
            self.actual_query = self.query.order_by(getattr(DBScore, self.sort_methods[self.sort][0]).desc())
        else:
            self.actual_query = self.query.order_by(getattr(DBScore, self.sort_methods[self.sort][0]).asc())
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @button(label="↓", style=discord.ButtonStyle.secondary)
    async def sort_direction(self, interaction: discord.Interaction, button: discord.ui.Button):
        if button.label == "↓":
            button.label = "↑"
            self.desc = False
            self.actual_query = self.query.order_by(getattr(DBScore, self.sort_methods[self.sort][0]).asc())
        else:
            button.label = "↓"
            self.desc = True
            self.actual_query = self.query.order_by(getattr(DBScore, self.sort_methods[self.sort][0]).desc())
        self.page = 0
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def simulate_pp(self, score: DBScore):
        pp_system = by_version(score.pp_system)
        if pp_system:
            fc_pp = pp_system.calculate_db_score(score, as_fc=True)
            ss_pp = pp_system.simulate(SimulatedScore(score.beatmap_id, score.mode, mods=score.mods))
            if not fc_pp:
                fc_pp = score.pp
        else:
            fc_pp = 0
            ss_pp = 0
        return fc_pp, ss_pp

    def get_embed(self) -> Embed:
        embed = Embed(color=discord.Color.blue())
        embed.title = f"{self.user.username}'s clears ({self.count}, page {self.page+1}/{int(self.count/self.length)+1})"
        embed.description = ""
        i = self.page*self.length
        for score in self.actual_query.offset(self.page*self.length).limit(self.length):
            i+=1
            score: DBScore = score
            fc_pp, ss_pp = self.simulate_pp(score)
            embed.description += f"{i}. **[{score.beatmap.get_title()}](https://osu.ppy.sh/b/{score.beatmap_id}) +{Mods(score.mods).short}**\n"
            embed.description += f"**PP**:    {score.pp:.0f}/{fc_pp:.0f} (SS: {ss_pp:.0f})\n"
            embed.description += f"**Stats**: __{score.count_300}/{score.count_100}/{score.count_50}/{score.count_miss}__ **{score.accuracy:.2f}%** __{score.max_combo}x/{score.beatmap.max_combo}x__ **{score.rank}** __{score.score:,}__\n"
            embed.description += f"**Date**:  {score.date}\n"
        return embed

    async def reply(self, message: Message):
        await message.reply(embed=self.get_embed(), view=self)

class ShowClearsCommand(Command):
    
    def __init__(self) -> None:
        super().__init__("showclears", "Show clears")
        
    async def run(self, message: Message, args: List[str]):
        parsed = self._parse_args(args)
        server = None
        username = 0
        mode = 0
        relax = 0

        if parsed['default']:
            username = parsed['default'][0]

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

        user, _ = server.get_user_info(username, mode, relax)

        query = database.session.query(DBScore).filter(
            DBScore.user_id == user.id,
            DBScore.mode == mode,
            DBScore.relax == relax,
            DBScore.server == server.server_name
        )
        
        if query.count() == 0:
            await message.reply(f"User {user.username} has no clears on {server.server_name}!")
            return
        
        await TopView(user, mode, relax, query).reply(message)
        