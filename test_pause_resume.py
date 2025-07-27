#!/usr/bin/env python3
"""
Test script to verify Prefect pause/resume functionality
"""
import asyncio
import websockets
import json
import uuid

async def test_chat_flow():
    # First, create a session
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/api/chat/start")
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Created session: {session_id}")
    
    # Connect to WebSocket
    uri = f"ws://localhost:8000/ws/{session_id}"
    
    async with websockets.connect(uri) as websocket:
        print(f"Connected to WebSocket")
        
        # Send first message
        message1 = {
            "type": "user_message",
            "message": "Hello, this is my first message!"
        }
        await websocket.send(json.dumps(message1))
        print(f"Sent: {message1}")
        
        # Listen for responses
        print("\n--- Waiting for responses ---")
        
        # Collect responses until flow pauses
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                print(f"Received: {data['type']} - {data.get('message', data)}")
                
                # Check if flow is paused
                if data.get("type") == "flow_status" and data.get("status") == "paused":
                    print("\n--- Flow is paused! Sending second message ---")
                    break
                    
            except asyncio.TimeoutError:
                print("Timeout waiting for response")
                break
        
        # Wait a bit before sending second message
        await asyncio.sleep(2)
        
        # Send second message to resume
        message2 = {
            "type": "user_message",
            "message": "This is my second message to resume the flow!"
        }
        await websocket.send(json.dumps(message2))
        print(f"\nSent: {message2}")
        
        # Listen for more responses
        print("\n--- Waiting for resumed flow responses ---")
        
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                print(f"Received: {data['type']} - {data.get('message', data)}")
                
                # Check if flow is paused again
                if data.get("type") == "flow_status" and data.get("status") == "paused":
                    print("\n--- Flow is paused again! ---")
                    break
                    
            except asyncio.TimeoutError:
                print("Timeout waiting for response")
                break
        
        # Send exit message
        message3 = {
            "type": "user_message",
            "message": "goodbye"
        }
        await websocket.send(json.dumps(message3))
        print(f"\nSent: {message3}")
        
        # Wait for final responses
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                print(f"Received: {data['type']} - {data.get('message', data)}")
                
                if data.get("type") == "flow_status" and data.get("status") == "completed":
                    print("\n--- Flow completed! ---")
                    break
                    
            except asyncio.TimeoutError:
                print("Done!")
                break

if __name__ == "__main__":
    asyncio.run(test_chat_flow())