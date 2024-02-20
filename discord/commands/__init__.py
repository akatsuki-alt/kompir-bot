from common.database.objects import DBBotLink
from common.app import database

from discord import Message

from enum import IntEnum
from typing import Dict, List, Tuple

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
    
    def _get_modes(self) -> Dict[str, Tuple[int, int]]:
        return {
            'std': (0, 0),
            'std_rx': (0, 1),
            'std_ap': (0, 2),
            'taiko': (1, 0),
            'taiko_rx': (1, 1),
            'ctb': (2,0),
            'ctb_rx': (2, 1),
            'mania': (3, 0),
        }
    
    def _get_mode_from_string(self, string: str) -> Tuple[int, int] | None:
        modes = self._get_modes()
        if string in modes:
            return modes[string]

    def _get_link(self, message: Message) -> DBBotLink:
        with database.session as session:
            return session.get(DBBotLink, message.author.id)

    async def _msg_not_linked(self, message: Message):
        await message.reply("This command requires a link! Use !link <username> <server> to link your account.")

    async def _msg_no_permission(self, message: Message):
        await message.reply("You do not have permission to use this command!")

    def _parse_args(self, args: List[str]) -> dict:
        result = {'default': list()}
        prev = None
        for arg in args:
            if arg.startswith('-') and not ' ' in arg:
                if prev:
                    result[prev] = None
                prev = arg[1:]
            else:
                if prev:
                    result[prev] = arg
                    prev = None
                else:
                    result['default'].append(arg)
        if prev:
            result[prev] = None
        return result

    async def run(self, message: Message, args: List[str]):
        pass

