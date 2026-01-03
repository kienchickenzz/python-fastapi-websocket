import asyncio
import io

from PIL import Image
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
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

    async def broadcast_image(self, image_data: bytes):
        """
        Broadcast ảnh với nhiều tùy chọn
        
        Args:
            image_data: Dữ liệu ảnh (bytes hoặc base64 string)
            image_type: "binary" hoặc "base64"
            metadata: Thông tin bổ sung (format, width, height, timestamp)
        """
        disconnected = []
        
        async with self.lock:
            connections = self.active_connections.copy()
        
        for connection in connections:
            try:
                await connection.send_bytes(image_data)
            except Exception as e:
                print(f"Error broadcasting image: {e}")
                disconnected.append(connection)
        
        # Xóa các kết nối bị lỗi
        for connection in disconnected:
            await self.disconnect(connection)
        
    async def broadcast_image_file(self, file_path: str):
        """Broadcast ảnh từ file"""
        try:
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
            await self.broadcast_image(image_bytes)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

manager = ConnectionManager()


@app.websocket("/ws/image")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Nhận ảnh từ client
            data = await websocket.receive_bytes()
            
            # Xử lý ảnh (ví dụ: resize)
            image = Image.open(io.BytesIO(data))
            image.thumbnail((800, 600))
            
            # Chuyển về bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()
            await manager.broadcast_image(img_byte_arr)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

@app.post("/broadcast/image")
async def broadcast_image_endpoint(file: UploadFile = File()):
    image_data = await file.read()
    await manager.broadcast_image(image_data)
    
    return {
        "status": "image broadcasted",
        "filename": file.filename,
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
    uvicorn.run('main:app', host="0.0.0.0", port=8001, reload=True)
