"""
FastAPI backend with dynamic Prefect flow execution
This version runs flows directly without deployments
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from typing import Dict
from datetime import datetime
import uuid

from prefect import flow, task, get_run_logger
from prefect.client.schemas.objects import State
import json
import os

# Store WebSocket connections
websocket_manager: Dict[str, WebSocket] = {}
# Store flow tasks
flow_tasks: Dict[str, asyncio.Task] = {}

# Set Prefect API URL if provided
if os.getenv("PREFECT_API_URL"):
    import prefect
    prefect.settings.PREFECT_API_URL = os.getenv("PREFECT_API_URL")


# Define flows inline for simplicity
@task(name="process-message", log_prints=True)
async def process_message(message: str, session_id: str, interaction: int):
    """Process user message"""
    print(f"[TASK] Processing message for {session_id}: {message}")
    
    # Send status via WebSocket
    if session_id in websocket_manager:
        await websocket_manager[session_id].send_json({
            "type": "task_status",
            "task": "process-message",
            "message": "Processing your message...",
            "timestamp": datetime.now().isoformat()
        })
    
    await asyncio.sleep(2)
    return {"message": message, "word_count": len(message.split()), "interaction": interaction}


@task(name="analyze-sentiment", log_prints=True)
async def analyze_sentiment(context: dict, session_id: str):
    """Analyze sentiment"""
    print(f"[TASK] Analyzing sentiment for {session_id}")
    
    if session_id in websocket_manager:
        await websocket_manager[session_id].send_json({
            "type": "task_status",
            "task": "analyze-sentiment",
            "message": "Analyzing sentiment...",
            "timestamp": datetime.now().isoformat()
        })
    
    await asyncio.sleep(1.5)
    sentiment = "positive" if "?" in context["message"] else "neutral"
    print(f"[TASK] Sentiment detected: {sentiment}")
    return sentiment


@task(name="generate-response", log_prints=True)
async def generate_response(context: dict, sentiment: str, session_id: str):
    """Generate response"""
    print(f"[TASK] Generating response for {session_id}")
    
    if session_id in websocket_manager:
        await websocket_manager[session_id].send_json({
            "type": "task_status",
            "task": "generate-response",
            "message": "Generating response...",
            "timestamp": datetime.now().isoformat()
        })
    
    await asyncio.sleep(2)
    
    interaction = context["interaction"]
    if interaction == 1:
        response = f"Hello! I received: '{context['message']}' ({sentiment} sentiment). This is a real Prefect flow!"
    else:
        response = f"Interaction {interaction}: Processing '{context['message']}' with {sentiment} sentiment."
    
    print(f"[TASK] Generated response: {response}")
    return response


@flow(name="chat-flow", log_prints=True)
async def chat_flow(session_id: str, message: str, interaction: int = 1):
    """Simple chat flow that runs once per message"""
    print(f"\n[FLOW] Starting chat flow for {session_id}, interaction {interaction}")
    print(f"[FLOW] Message: {message}")
    
    # Send flow start status
    if session_id in websocket_manager:
        await websocket_manager[session_id].send_json({
            "type": "status",
            "message": f"{'Starting' if interaction == 1 else 'Resuming'} Prefect flow...",
            "timestamp": datetime.now().isoformat()
        })
    
    # Execute tasks
    print("[FLOW] Executing task 1: process_message")
    context = await process_message(message, session_id, interaction)
    
    print("[FLOW] Executing task 2: analyze_sentiment")
    sentiment = await analyze_sentiment(context, session_id)
    
    print("[FLOW] Executing task 3: generate_response")
    response = await generate_response(context, sentiment, session_id)
    
    # Send response
    if session_id in websocket_manager:
        await websocket_manager[session_id].send_json({
            "type": "agent_message",
            "message": response,
            "interaction": interaction,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat()
        })
    
    print(f"[FLOW] Flow completed for interaction {interaction}\n")
    return {"response": response, "sentiment": sentiment}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting FastAPI with dynamic Prefect flows...")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Chat Agent with Dynamic Prefect",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(websocket_manager),
        "active_flows": len(flow_tasks)
    }


@app.post("/api/chat/start")
async def start_chat_session():
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    print(f"\n=== NEW SESSION: {session_id} ===\n")
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat()
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    websocket_manager[session_id] = websocket
    print(f"\n=== WEBSOCKET CONNECTED: {session_id} ===\n")
    
    interaction_count = 0
    
    try:
        while True:
            data = await websocket.receive_json()
            print(f"\n=== RECEIVED: {data} ===\n")
            
            if data.get("type") == "user_message":
                message = data.get("message", "")
                interaction_count += 1
                
                print(f"\n[WS] Triggering Prefect flow for message: {message}")
                print(f"[WS] Session: {session_id}, Interaction: {interaction_count}")
                
                # Run the flow directly
                try:
                    # Execute the flow asynchronously
                    print("[WS] Creating flow task...")
                    flow_task = asyncio.create_task(
                        chat_flow(session_id, message, interaction_count)
                    )
                    flow_tasks[session_id] = flow_task
                    
                    # Wait for completion
                    print("[WS] Waiting for flow to complete...")
                    result = await flow_task
                    print(f"[WS] Flow completed with result: {result}")
                    
                except Exception as e:
                    print(f"[WS] Flow execution error: {e}")
                    import traceback
                    traceback.print_exc()
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Flow error: {str(e)}"
                    })
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
    finally:
        websocket_manager.pop(session_id, None)
        if session_id in flow_tasks:
            flow_tasks.pop(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)