from fastapi import WebSocket
from typing import Dict
from app.logger import get_logger

logger = get_logger("websocket_manager")

class ConnectionManager:
    def __init__(self) -> None:
        self.activeConnections: Dict[int, WebSocket] = {}

    async def connect(self, userId, websocket: WebSocket):
        await websocket.accept()

        old_ws = self.activeConnections.get(userId)
        if old_ws:
            try:
                await old_ws.close(code=1000)
                logger.info("Closed previous connection for user", extra={"user_id": userId})
            except Exception as e:
                logger.warning(f"Error closing old connection: {e}", extra={"user_id": userId})
        
        self.activeConnections[userId] = websocket

        logger.info("User connected via WebSocket", extra={
            "user_id": userId, 
            "total_active_connections": len(self.activeConnections)
        })
    
    async def disconnect(self, userId):
        ws = self.activeConnections.get(userId)
        if ws:
            try:
                await ws.close(code=1000)
            except Exception:
                pass 

            if userId in self.activeConnections:
                del self.activeConnections[userId]
                
            logger.info("User disconnected", extra={
                "user_id": userId, 
                "total_active_connections": len(self.activeConnections)
            })
        
    async def sendToUser(self, userId):
        ws = self.activeConnections.get(userId)
        if ws:
            try:
                logger.info("Pushing 'meal_ready' event to client", extra={"user_id": userId})
                await ws.send_json({"event": "meal_ready"})
            except Exception as e:
                logger.error(f"Failed to send WS message: {e}", extra={"user_id": userId})
                await self.disconnect(userId)
        else:
            logger.warning("Attempted to notify disconnected user", extra={"user_id": userId})
        
manager = ConnectionManager()
    