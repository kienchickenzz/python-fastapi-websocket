import asyncio

import websockets


URL = "ws://localhost:8001/ws/text"

async def websocket_client(uri: str):
    async with websockets.connect(uri) as websocket:
        # Tạo task để nhận tin nhắn từ server
        receive_task = asyncio.create_task(receive_messages(websocket))
        
        # Chờ task hoàn thành
        await asyncio.gather(receive_task)
            
async def receive_messages(websocket):
    async for message in websocket:
        print(f"[Message] {message}")

def main():
    try:
        asyncio.run(websocket_client(URL))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":

    main()
