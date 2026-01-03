import json
from datetime import datetime
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


app = FastAPI(title="WebSocket API")

# Lưu trữ các kết nối WebSocket đang active
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.lock = asyncio.Lock()  # Để tránh race condition

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
        print(f"New connection. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            self.active_connections.remove(websocket)
        print(f"Connection closed. Total connections: {len(self.active_connections)}")

    async def send_text(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_text(self, message: str):
        async with self.lock:
            connections = self.active_connections.copy()
        for connection in connections:
            try:
                await connection.send_text(message)
            except:
                pass

    async def broadcast_text_except(self, message: str, exclude: WebSocket):
        async with self.lock:
            connections = self.active_connections.copy()
        for connection in connections:
            if connection != exclude:
                try:
                    await connection.send_text(message)
                except:
                    pass

manager = ConnectionManager()

# Endpoint WebSocket
@app.websocket("/ws/text")
async def websocket_text(websocket: WebSocket):
    client_id = id(websocket)
    await manager.connect(websocket)
    
    try:
        # Gửi welcome message
        await manager.send_text(
            json.dumps({
                "type": "system",
                "message": f"Connected successfully! Your ID: {client_id}",
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )
        
        # Broadcast khi có user mới kết nối
        await manager.broadcast_text(
            json.dumps({
                "type": "notification",
                "message": f"New user joined. Total users: {len(manager.active_connections)}",
                "timestamp": datetime.now().isoformat()
            })
        )
        
        # Xử lý tin nhắn từ client
        while True:
            text = await websocket.receive_text()
            await manager.broadcast_text_except(text, websocket)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

# Endpoint để test broadcast message từ server
@app.post("/broadcast/text")
async def broadcast_message(message: str):
    await manager.broadcast_text(
        json.dumps({
            "type": "broadcast",
            "from": "server",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
    )
    return {
        "status": "message broadcasted", 
        "text": message,
        "recipients": len(manager.active_connections)
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "*"],  # Hoặc cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    uvicorn.run('ws_text:app', host="0.0.0.0", port=8001, reload=True)
