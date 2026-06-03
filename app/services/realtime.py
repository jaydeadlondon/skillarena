from collections import defaultdict
from typing import Any

from starlette.websockets import WebSocket


class BattleConnectionManager:
    def __init__(self) -> None:
        self._battle_connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, battle_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._battle_connections[battle_id].add(websocket)
        await self.broadcast(
            battle_id,
            {
                "type": "presence",
                "connections": len(self._battle_connections[battle_id]),
            },
        )

    async def disconnect(self, battle_id: int, websocket: WebSocket) -> None:
        connections = self._battle_connections.get(battle_id)
        if not connections:
            return
        connections.discard(websocket)
        if connections:
            await self.broadcast(
                battle_id, {"type": "presence", "connections": len(connections)}
            )
        else:
            self._battle_connections.pop(battle_id, None)

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
