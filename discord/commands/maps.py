import io
from typing import List
from discord import Button, ButtonStyle, Embed, File, Interaction, Message
from . import Command
from discord.ui import View, button
from wrapper.akatsuki_alt_api.api import instance as api

SORT_METHODS = ["id", "set_id", "max_combo", "bpm", "total_length", "hit_length", "diff"]

class MapsView(View):

    def __init__(self, query: str, sort: int, desc: bool, **api_options):
        super().__init__()
        self.query = api.query_beatmaps(query, **api_options)
        self.current_sort = sort
        self.desc = desc
        self.query.set_sort(SORT_METHODS[self.current_sort], self.desc)
        for c in self.children:
            if c.label.startswith("Sort:"):
                c.label = f"Sort: {SORT_METHODS[self.current_sort]}"
            if c.label.startswith("Order:"):
                if self.desc:
                    c.label = "Order: ↓"
                else:
                    c.label = "Order: ↑"

    @button(label="Previous", style=ButtonStyle.gray)
    async def prev_button(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        await interaction.message.edit(embed=self.get_embed(self.query.prev()), view=self)

    @button(label="Next", style=ButtonStyle.gray)
    async def next_button(self, interaction: Interaction, button: Button):
        if self.query._page >= max(1, self.query.count/7):
            return
        await interaction.response.defer()   
        await interaction.message.edit(embed=self.get_embed(self.query.next()), view=self)

    @button(label=f"Sort: set_id", style=ButtonStyle.green)
    async def sort_button(self, interaction: Interaction, button: Button):
        self.current_sort += 1
        if self.current_sort >= len(SORT_METHODS):
            self.current_sort = 0
        self.query.set_sort(SORT_METHODS[self.current_sort], self.desc)
        button.label = f"Sort: {SORT_METHODS[self.current_sort]}"
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
        self.query.set_sort(SORT_METHODS[self.current_sort], self.desc)
        await interaction.message.edit(embed=self.get_embed(), view=self)

    def get_embed(self, beatmaps = None) -> Embed:
        if beatmaps is None:
            beatmaps = self.query.next()
        title = f"Maps (Total: {self.query.count}, Page: {self.query._page}/{max(1, self.query.count/7):.0f})"
        embed = Embed(title=title)
        for beatmap in beatmaps:
            title = f"{beatmap.beatmapset.artist} - {beatmap.beatmapset.title} [{beatmap.version}]"
            desc = f"SR: {beatmap.diff:.2f}* | Length: {beatmap.total_length/60:.0f} mins | Max combo: {beatmap.max_combo}x | [Bancho](https://osu.ppy.sh/b/{beatmap.id})"
            if beatmap.beatmapset.pack_tags:
                title += f" ({' '.join(beatmap.beatmapset.pack_tags)})"
            embed.add_field(name=title[:255], value=desc[:1023], inline=False)   
        return embed
    
    async def reply(self, message: Message):
        await message.reply(embed=self.get_embed(), view=self)

class SearchMapsCommand(Command):
    
    def __init__(self):
        super().__init__("searchmaps", "Search maps")

    async def run(self, message: Message, args: List[str]):
        parsed = self._parse_args(args)
        sort = 1
        desc = True
        if 'sort' in parsed:
            if parsed['sort'] in SORT_METHODS:
                sort = SORT_METHODS.index(parsed['sort'])
            else:
                await message.reply(f"Invalid sort method! Valid options: {', '.join(SORT_METHODS)}")
                return
        if 'desc' in parsed:
            if parsed['desc'].lower() == 'true':
                desc = True
            else:
                desc = False
        query = ",".join(parsed['default']) if args else ""
        if 'csv' in parsed:
            api_query = api.query_beatmaps(query, 1000, sort, desc)
            api_query.set_sort(SORT_METHODS[sort], desc)
            csv = ""
            while beatmaps := api_query.next():
                if api_query.count > 10000:
                    await message.reply("Too many results! Please refine your search.")
                    return
                if not csv:
                    for k in beatmaps[0].beatmapset.__dict__.keys():
                        if k.startswith("_") or k.startswith("id"):
                            continue
                        csv += f"{k}\t"
                    for k in beatmaps[0].__dict__.keys():
                        if k.startswith("_") or k == "beatmapset":
                            continue
                        csv += f"{k}\t"
                    csv += "\n"
                for beatmap in beatmaps:
                    for k,v in beatmap.beatmapset.__dict__.items():
                        if k.startswith("_") or k.startswith("id"):
                            continue
                        csv += f"{v}\t"
                    for k,v in beatmap.__dict__.items():
                        if k.startswith("_") or k == "beatmapset":
                            continue
                        csv += f"{v}\t"
                    csv += "\n"
            await message.reply(file=File(io.StringIO(csv), filename="maps.csv"))
        else:
            await MapsView(query, sort, desc, length=7).reply(message)