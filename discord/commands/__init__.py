from common.database.objects import DBBotLink
from common.app import database

from discord import Message

from enum import IntEnum
from typing import Dict, List, Tuple

import common.servers as servers

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

    def _get_mode_full_name(self, mode: int, relax: int):
        modes = {
            0: 'Standard',
            1: 'Taiko',
            2: 'Ctb',
            3: 'Mania'
        }
        relaxs = {
            0: '',
            1: 'Relax',
            2: 'Autopilot'
        }
        return f'{modes[mode]} {relaxs[relax]}'.strip()
    
    def _get_mode_from_string(self, string: str) -> Tuple[int, int] | None:
        modes = self._get_modes()
        if string in modes:
            return modes[string]

    def _get_link(self, message: Message) -> DBBotLink:
        with database.managed_session() as session:
            return session.get(DBBotLink, message.author.id)

    async def _msg_not_linked(self, message: Message):
        await message.reply("This command requires a link! Use !link <username> <server> to link your account.")

    async def _msg_no_permission(self, message: Message):
        await message.reply("You do not have permission to use this command!")

    def _parse_args(self, args: List[str]) -> dict:
        modes = self._get_modes()
        server_names = [x.server_name for x in servers.servers]
        result = {'default': list()}
        prev = None
        def handle_shortcuts():
            if prev in modes:
                result['mode'] = modes[prev]
            elif prev in server_names:
                result['server'] = prev
            else:
                result[prev] = None
        for arg in args:
            if arg.startswith('-') and not ' ' in arg:
                if prev:
                    handle_shortcuts()
                prev = arg[1:]
            else:
                if prev:
                    result[prev] = arg
                    prev = None
                else:
                    result['default'].append(arg)
        if prev:
            handle_shortcuts()
        return result

    async def run(self, message: Message, args: List[str]):
        pass

