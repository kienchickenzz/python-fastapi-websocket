import asyncio
import sys
import argparse

import websockets
from websockets.asyncio.client import ClientConnection


URL = "ws://localhost:8001/ws/text"

async def websocket_client(uri: str):
    async with websockets.connect(uri) as websocket:
        # Tạo task để nhận tin nhắn từ server
        receive_task = asyncio.create_task(receive_messages(websocket))
        # Tạo task để gửi tin nhắn từ stdin
        send_task = asyncio.create_task(send_messages(websocket))
        
        # Chờ cả hai task hoàn thành
        await asyncio.gather(receive_task, send_task)


async def receive_messages(websocket):
    async for message in websocket:
        print(f"[Message] {message}")


async def send_messages(websocket: ClientConnection):
    while True:
        # Đọc input từ stdin không blocking
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, sys.stdin.readline)
        
        if not text:
            break
            
        text = text.strip()
        if text:
            await websocket.send(text)
             
                    
def main(url: str):
    try:
        asyncio.run(websocket_client(url))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser("Websocket Client")

    parser.add_argument("--target_client_id", type=str, required=True, help="ID của client mục tiêu để gửi tin nhắn")

    options = parser.parse_args()

    url = f"{URL}/{options.target_client_id}"
    main(url)
