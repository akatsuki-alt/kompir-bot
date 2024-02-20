from . import PermissionLevelEnum, Command

from discord import Message, File
from sqlalchemy import text
from typing import List

import common.app as app
import io

class DatabaseQueryCommand(Command):
    
    def __init__(self) -> None:
        super().__init__("query", "query the database", permission_level=PermissionLevelEnum.ADVANCED)
        
    async def run(self, message: Message, args: List[str]):
        with app.database.engine_ro.connect() as conn:
            tsv = ""
            try:
                rs = conn.execute(text(" ".join(message.content.split(" ")[1:])))
                for row in rs:
                    tsv += "\t".join([str(x) for x in row]) + "\n"
                await message.reply(file=File(io.StringIO(tsv), filename="query.tsv"))
            except Exception as e:
                await message.reply(f"Query error: {repr(e)}")