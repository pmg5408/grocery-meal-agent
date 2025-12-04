from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self) -> None:
        self.activeConnections: Dict[int, WebSocket] = {}

    async def connect(self, userId, websocket: WebSocket):
        await websocket.accept()
        self.activeConnections[userId] = websocket
    
    def disconnect(self, userId):
        if userId in self.activeConnections:
            del self.activeConnections[userId]
        
    async def sendToUser(self, userId, message):
        websocket = self.activeConnections[userId]
        if websocket:
            await websocket.send_json({"mealWindow": message["mealWindow"]})
        
manager = ConnectionManager()
    