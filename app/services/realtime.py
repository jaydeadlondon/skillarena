from collections import defaultdict
from typing import Any

from starlette.websockets import WebSocket

LIVE_PVP_ROUND_SECONDS = 60
PVP_DEADLINE_GRACE_SECONDS = 5


class BattleConnectionManager:
    def __init__(self) -> None:
        self._battle_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._ready_users: dict[int, set[int]] = defaultdict(set)
        self._started_battles: set[int] = set()

    async def connect(self, battle_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._battle_connections[battle_id].add(websocket)
        await self.broadcast_presence(battle_id)

    async def disconnect(self, battle_id: int, websocket: WebSocket) -> None:
        connections = self._battle_connections.get(battle_id)
        if not connections:
            return
        connections.discard(websocket)
        if connections:
            await self.broadcast_presence(battle_id)
        else:
            self._battle_connections.pop(battle_id, None)
            self._ready_users.pop(battle_id, None)
            self._started_battles.discard(battle_id)

    async def mark_ready(self, battle_id: int, user_id: int) -> bool:
        self._ready_users[battle_id].add(user_id)
        await self.broadcast(
            battle_id,
            {
                "type": "ready",
                "user_id": user_id,
                "battle_id": battle_id,
                "ready_count": len(self._ready_users[battle_id]),
            },
        )
        if (
            len(self._ready_users[battle_id]) >= 2
            and battle_id not in self._started_battles
        ):
            self._started_battles.add(battle_id)
            return True
        return False

    async def broadcast_presence(self, battle_id: int) -> None:
        await self.broadcast(
            battle_id,
            {
                "type": "presence",
                "connections": len(self._battle_connections.get(battle_id, set())),
                "ready_count": len(self._ready_users.get(battle_id, set())),
                "started": battle_id in self._started_battles,
            },
        )

    async def broadcast(self, battle_id: int, message: dict[str, Any]) -> None:
        connections = list(self._battle_connections.get(battle_id, set()))
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.disconnect(battle_id, websocket)


pvp_battle_manager = BattleConnectionManager()
