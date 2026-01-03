import asyncio

import websockets
import cv2
import numpy as np


URI = "ws://localhost:8001/ws/image"

async def receive_images():
    async with websockets.connect(URI) as websocket:
        image_count = 0
        
        while True:
            try:
                # Nhận dữ liệu byte từ WebSocket
                byte_data = await websocket.recv()
                # Chuyển byte thành mảng numpy
                nparr = np.frombuffer(byte_data, np.uint8)

                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # Giải mã ảnh
                if img is not None:
                    # Lưu ảnh
                    filename = f"image_{image_count}.jpg"
                    cv2.imwrite(filename, img)
                    print(f"Đã lưu: {filename}")
                    image_count += 1
                else:
                    print("Không thể giải mã ảnh")
                    
            except Exception as e:
                print(f"Error: {e}")
                break

if __name__ == "__main__":
    asyncio.run(receive_images())
