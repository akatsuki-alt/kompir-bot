import io
from common.database.objects import DBBeatmapset, DBBeatmap
from sqlalchemy import Integer
from common.app import database
from discord import File, Message
from typing import List

from . import Command

class GetFileCommand(Command):
    def __init__(self) -> None:
        super().__init__("getfile", "Get private server custom beatmaps", "Usage: !getfile <server> <beatmapsets/beatmaps> [status_integer]")

    def _generate_beatmaps_tsv(self, server: str, status: int | None = None):
        tsv = ""
        with database.managed_session() as session:
            query = session.query(DBBeatmap).filter(DBBeatmap.status[server].astext.cast(Integer) != DBBeatmap.status["bancho"].astext.cast(Integer))
            if status is not None:
                query = query.filter(DBBeatmap.status[server].astext.cast(Integer) == status)
            else:
                query = query.filter(DBBeatmap.status[server].astext.cast(Integer) > 0)
            beatmap = query.first()
            if not beatmap:
                return "" # Something wrong happened
            if not tsv:
                tsv += "\t".join([str(x) for x in beatmap.__dict__.keys() if not x.startswith("_")]) + "\n"
            for beatmap in query:
                tsv += "\t".join([str(v) for k,v in beatmap.__dict__.items() if not k.startswith("_")]) + "\n"
        return tsv

    def _generate_beatmapsets_tsv(self, server: str, status: int | None = None):
        tsv = ""
        with database.managed_session() as session:
            query = session.query(DBBeatmapset).join(DBBeatmap).filter(DBBeatmap.status[server].astext.cast(Integer) != DBBeatmap.status["bancho"].astext.cast(Integer))
            if status is not None:
                query = query.filter(DBBeatmap.status[server].astext.cast(Integer) == status)
            else:
                query = query.filter(DBBeatmap.status[server].astext.cast(Integer) > 0)
            beatmapset = query.first()
            if not beatmapset:
                return "" # Something wrong happened
            if not tsv:
                tsv += "\t".join([str(x) for x in beatmapset.__dict__.keys() if not x.startswith("_")]) + "\n"
            for beatmapset in query:
                tsv += "\t".join([str(v) for k,v in beatmapset.__dict__.items() if not k.startswith("_")]) + "\n"
        return tsv


    async def run(self, message: Message, args: List[str]):
        if len(args) < 2:
            await message.reply("Usage: !getfile <server> <beatmapsets/beatmaps> [status_integer]")
            return
        if args[1] == "beatmapsets":
            tsv = self._generate_beatmapsets_tsv(args[0], args[2] if len(args) == 3 else None)
        elif args[1] == "beatmaps":
            tsv = self._generate_beatmaps_tsv(args[0], args[2] if len(args) == 3 else None)
        else:
            await message.reply("Usage: !getfile <server> <beatmapsets/beatmaps> [status_integer]")
            return
        if not tsv:
            await message.reply("No beatmaps found!")
            return
        await message.reply(file=File(io.StringIO(tsv), filename=f"{args[2]}.tsv"))