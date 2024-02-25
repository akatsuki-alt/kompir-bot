from common.performance import by_version, SimulatedScore
from common.constants import Mods, BeatmapStatus
from common.database.objects import DBBeatmap
from common.utils import MapStats

from discord import Embed, Message, Color
from typing import List
from . import Command

import common.servers as servers
import common.app as app

class RecentCommand(Command):
    
    def __init__(self):
        super().__init__("recent", "Show recent play on a user")
        
    async def run(self, message: Message, args: List[str]):
        user = None
        server = None
        mode = -1
        relax = -1
        modes = self._get_modes()
        for arg in args:
            if arg.startswith('-') and not ' ' in arg:
                if arg[1:] in modes:
                    mode, relax = modes[arg[1:]]
                    continue
                if not (server := servers.by_name(arg[1:])):
                    await message.reply(f"Unknown server: {arg[1:]}! Use !servers to see available servers.")
                    return
            else:
                user = arg
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
            user = server.get_user_info(link.links[server.server_name])[0]
            if not user:
                await message.reply(f"User not found on {server.server_name}!")
                return
        else:
            user = server.get_user_info(user)[0]
            if not user:
                await message.reply(f"User not found on {server.server_name}!")
                return
        if mode == -1:
            if link:
                mode = link.default_mode
                relax = link.default_relax
            else:
                mode = 0
                relax = 0
        recent_plays = server.get_user_recent(user.id, mode, relax)
        
        if not recent_plays:
            await message.reply(f"No recent plays found for {user.username} on {server.server_name}.")
            return
        
        retries = 0
        total_playcount = 0 # TODO
        
        for play in recent_plays:
            if play.beatmap_id != recent_plays[0].beatmap_id:
                break
            retries += 1
        
        play = recent_plays[0]
        
        with app.database.managed_session() as session:
            beatmap = session.get(DBBeatmap, play.beatmap_id)
            if not beatmap or not beatmap.beatmapset:
                await message.reply(f"Beatmap not found???")
                return
            session.expunge(beatmap.beatmapset)

        pp_system = by_version(server.get_pp_system(mode, relax))
        if pp_system:
            fc_pp = pp_system.calculate_score(recent_plays[0], as_fc=True)
            ss_pp = pp_system.simulate(SimulatedScore(beatmap.id, mode, mods=play.mods))
        else:
            fc_pp = 0
            ss_pp = 0
            
        status = beatmap.status[server.server_name] if server.server_name in beatmap.status else -2

        completion = ""
        if play.completed < 2:
            completion = f"({(play.get_total_hits() / beatmap.get_total_hits()) * 100:.2f}%)"
        
        map_stats = MapStats(mods=play.mods, ar=beatmap.ar, od=beatmap.od, hp=beatmap.hp, cs=beatmap.cs, bpm=beatmap.bpm)
        
        beatmap_info = f" AR: {map_stats.ar:.1f}, OD: {map_stats.od:.1f}, CS: {map_stats.cs:.1f}, HP: {map_stats.hp:.1f}, BPM: {map_stats.bpm:.0f}"
        play_info =  f" **Stats**: {play.count_300}/{play.count_100}/{play.count_50}/{play.count_miss} {play.accuracy:.2f}% {play.max_combo}/{beatmap.max_combo}x **{play.rank} +{Mods(play.mods).short} {completion}** {play.score:,}\n"
        play_info += f" **PP**: {play.pp:.2f}/{fc_pp:.2f} (SS: {ss_pp:.2f})\n"
        embed = Embed(color=Color.red(), title=f"Recent play for {user.username} on {server.server_name}")
        embed.description = f"**[{beatmap.get_title()}]({beatmap.get_url()})**\n{beatmap_info}"
        embed.add_field(name="Play info", value=play_info, inline=False)
        embed.set_footer(text=f"Try #{retries}, Total playcount: {total_playcount}, Play ID: {play.id}, {BeatmapStatus(status).name}")
        embed.set_thumbnail(url=f"https://b.ppy.sh/thumb/{beatmap.set_id}l.jpg")
        
        if play.completed == 3:
            embed.set_footer(text=embed.footer.text+", Personal best")
        elif play.completed == 4:
            embed.set_footer(text=embed.footer.text+", Personal best for mods combo")
        
        await message.reply(embed=embed)
