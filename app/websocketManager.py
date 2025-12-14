from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self) -> None:
        self.activeConnections: Dict[int, WebSocket] = {}

    async def connect(self, userId, websocket: WebSocket):
        await websocket.accept()
        old_ws = self.activeConnections.get(userId)
        if old_ws:
            try:
                await old_ws.close(code=1000)
            except:
                pass
        self.activeConnections[userId] = websocket
    
    async def disconnect(self, userId):
        ws = self.activeConnections.get(userId)
        if ws:
            try:
                await ws.close(code=1000)
            except:
                pass
            del self.activeConnections[userId]
        
    async def sendToUser(self, userId):
        ws = self.activeConnections.get(userId)
        if ws:
            try:
                await ws.send_json({"event": "meal_ready"})
            except Exception:
                # Client disconnected unexpectedly
                try:
                    await ws.close()
                except:
                    pass
                self.activeConnections.pop(userId, None)
        
manager = ConnectionManager()
    