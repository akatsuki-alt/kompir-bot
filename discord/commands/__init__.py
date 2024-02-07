from discord import Message

from enum import IntEnum
from typing import List

class PermissionLevelEnum(IntEnum):
    
    USER = 0
    ADVANCED = 1
    ADMIN = 2
    
class Command:
    
    def __init__(self, name: str, description = "No description provided.", help = "No help provided.", aliases: List[str] = [], permission_level: PermissionLevelEnum = PermissionLevelEnum.USER) -> None:
        self.name = name
        self.description = description
        self.help = help
        self.aliases = aliases
        self.permission_level = permission_level
    
    async def run(self, message: Message, args: List[str]):
        pass

