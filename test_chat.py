#!/usr/bin/env python3
"""
Simple test script to verify the chat system works
"""
import asyncio
import websockets
import json
from datetime import datetime


async def test_chat():
    # First, start a session
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/api/chat/start")
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Started session: {session_id}")
    
    # Connect via WebSocket
    uri = f"ws://localhost:8000/ws/{session_id}"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        # Test messages
        test_messages = [
            "Hello, this is my first message!",
            "Can you help me with something?",
            "That's interesting, tell me more.",
            "goodbye"
        ]
        
        for i, message in enumerate(test_messages):
            print(f"\n--- Sending message {i+1}: {message} ---")
            
            # Send message
            await websocket.send(json.dumps({
                "type": "user_message",
                "message": message
            }))
            
            # Receive responses
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(response)
                    
                    if data["type"] == "status":
                        print(f"Status: {data['message']}")
                    elif data["type"] == "agent_message":
                        print(f"Agent: {data['message']}")
                        print(f"(Interaction {data.get('interaction', 'N/A')})")
                        break
                    elif data["type"] == "error":
                        print(f"Error: {data['message']}")
                        break
                        
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
            
            # Wait a bit before next message
            await asyncio.sleep(1)
        
        print("\nChat test completed!")


if __name__ == "__main__":
    asyncio.run(test_chat())