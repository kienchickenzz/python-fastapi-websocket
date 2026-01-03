import json
from datetime import datetime
import asyncio
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


app = FastAPI(title="WebSocket API")

# Lưu trữ các kết nối WebSocket đang active
class ConnectionManager:
    def __init__(self):
        # Lưu connection theo ID để truy xuất nhanh
        self.active_connections: dict[str, WebSocket] = {}
        # Lưu metadata nếu cần (user_id, session info, etc.)
        self.connection_metadata: dict[str, dict] = {}
        
        self.lock = asyncio.Lock()  # Để tránh race condition


    async def connect(self, websocket: WebSocket) -> str:
        """_summary_

        Args:
            websocket (WebSocket): _description_

        Returns:
            str: _description_
        """
        await websocket.accept()

        connection_id = str(uuid.uuid4()) # Tạo ID duy nhất cho kết nối

        async with self.lock:
            self.active_connections[connection_id] = websocket
            self.connection_metadata[connection_id] = {
                'connected_at': asyncio.get_event_loop().time(),
                'last_active': asyncio.get_event_loop().time()
            }

        print(f"New connection. Total connections: {len(self.active_connections)}")
        return connection_id


    async def disconnect(self, connection_id: str):
        """_summary_

        Args:
            connection_id (str): _description_
        """
        async with self.lock:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
                del self.connection_metadata[connection_id]

        print(f"Connection closed. Total connections: {len(self.active_connections)}")


    def get_connection_by_id(self, connection_id: str) -> WebSocket | None:
        """_summary_

        Args:
            connection_id (str): _description_

        Returns:
            WebSocket | None: _description_
        """
        return self.active_connections.get(connection_id, None)


    async def send_text_to_client(self, message: str, connection_id: str):
        """_summary_

        Args:
            message (str): _description_
            connection_id (str): _description_

        Raises:
            ConnectionError: _description_
        """
        websocket = self.get_connection_by_id(connection_id)
        if not websocket:
            raise ConnectionError(f"Connection {connection_id} not found")
        
        if websocket:
            await websocket.send_text(message)


    async def broadcast_text(self, message: str):
        """_summary_

        Args:
            message (str): _description_
        """
        async with self.lock:
            connections = self.active_connections.copy()
        for connection in connections.values():
            try:
                await connection.send_text(message)
            except:
                pass


    async def broadcast_text_except_self(self, message: str, exclude_id: str):
        """_summary_

        Args:
            message (str): _description_
            exclude_id (str): _description_
        """
        async with self.lock:
            connections = self.active_connections.copy()
        for connection_id, connection in connections.items():
            if connection_id != exclude_id:
                try:
                    await connection.send_text(message)
                except:
                    pass


manager = ConnectionManager()


@app.websocket("/ws/text")
async def websocket_text(websocket: WebSocket):
    """_summary_

    Args:
        websocket (WebSocket): _description_
    """
    conn_id = await manager.connect(websocket)
    
    try:
        # Gửi welcome message
        await manager.send_text_to_client(
            f"Connected successfully! Your ID: {conn_id}",
            conn_id
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
            await manager.broadcast_text_except_self(text, conn_id)
    
    except WebSocketDisconnect:
        await manager.disconnect(conn_id)


@app.websocket("/ws/text/{target_client_id}")
async def websocket_endpoint(websocket: WebSocket, target_client_id: str):
    conn_id = await manager.connect(websocket)
    
    try:
        # Gửi welcome message
        await manager.send_text_to_client(
            f"Connected successfully! Your ID: {conn_id}",
            conn_id
        )

        # Xử lý tin nhắn từ client
        while True:
            data = await websocket.receive_text()
            # Gửi tin nhắn đến client mục tiêu
            await manager.send_text_to_client(data, target_client_id)
    
    except WebSocketDisconnect:
        await manager.disconnect(conn_id)


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
