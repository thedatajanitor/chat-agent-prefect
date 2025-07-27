"""
Chat Agent Backend with Real Prefect Flow Orchestration
Demonstrates pause/resume functionality with WebSocket communication
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from typing import Dict, Optional
from datetime import datetime
import uuid
import os

from prefect import flow, task, get_run_logger, pause_flow_run
from prefect.input import RunInput
from prefect.client.schemas.objects import State
import json

# Store WebSocket connections
websocket_manager: Dict[str, WebSocket] = {}
# Store flow states
flow_states: Dict[str, dict] = {}  # session_id -> flow state

# Set Prefect API URL if provided
if os.getenv("PREFECT_API_URL"):
    import prefect
    prefect.settings.PREFECT_API_URL = os.getenv("PREFECT_API_URL")


class UserMessage(RunInput):
    """Input model for user messages during pause"""
    message: str


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
    
    message = context["message"].lower()
    if "?" in message:
        sentiment = "curious"
    elif any(word in message for word in ["thanks", "great", "good", "love"]):
        sentiment = "positive"
    elif any(word in message for word in ["bad", "wrong", "issue", "problem"]):
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
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
        response = f"Hello! I received: '{context['message']}' ({sentiment} sentiment). This Prefect flow is now pausing. Send another message to resume!"
    elif interaction == 2:
        response = f"Thanks for resuming! You said: '{context['message']}' ({sentiment}). This demonstrates Prefect's pause/resume functionality."
    else:
        response = f"Interaction #{interaction}: Your {sentiment} message has been processed through the Prefect flow."
    
    print(f"[TASK] Generated response: {response}")
    return response


@flow(name="chat-conversation-flow", log_prints=True)
async def chat_conversation_flow(session_id: str, initial_message: str):
    """
    Main chat flow with pause/resume capability
    """
    print(f"\n[FLOW] Starting conversation flow for {session_id}")
    
    conversation_history = []
    interaction = 0
    message = initial_message
    
    while interaction < 10:  # Safety limit
        interaction += 1
        print(f"\n[FLOW] === Interaction {interaction} ===")
        
        # Send flow status
        if session_id in websocket_manager:
            await websocket_manager[session_id].send_json({
                "type": "status",
                "message": f"{'Starting' if interaction == 1 else 'Resuming'} Prefect flow (interaction {interaction})...",
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
        
        # Store in history
        conversation_history.append({
            "interaction": interaction,
            "user": message,
            "agent": response,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check for exit
        if any(word in message.lower() for word in ["exit", "goodbye", "bye"]):
            print("[FLOW] User requested exit")
            if session_id in websocket_manager:
                await websocket_manager[session_id].send_json({
                    "type": "status",
                    "message": "Flow completed. Thank you for chatting!"
                })
            break
        
        # Pause and wait for user input
        print("[FLOW] Pausing flow to wait for user input...")
        if session_id in websocket_manager:
            await websocket_manager[session_id].send_json({
                "type": "status",
                "message": "Flow paused. Send a message to resume..."
            })
        
        # Store flow state
        flow_states[session_id] = {
            "status": "paused",
            "interaction": interaction,
            "waiting_for_input": True
        }
        
        # Pause the flow
        user_input = await pause_flow_run(
            wait_for_input=UserMessage,
            timeout=300  # 5 minute timeout
        )
        
        if not user_input:
            print("[FLOW] Timeout waiting for user input")
            break
        
        message = user_input.message
        print(f"[FLOW] Received user input: {message}")
    
    print(f"[FLOW] Flow completed for {session_id}")
    return {
        "session_id": session_id,
        "total_interactions": interaction,
        "history": conversation_history
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Chat Agent with Real Prefect Flows...")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Chat Agent with Prefect Orchestration",
    version="2.0.0",
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
        "paused_flows": len([s for s in flow_states.values() if s.get("status") == "paused"])
    }


@app.post("/api/chat/start")
async def start_chat_session():
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    print(f"\n=== NEW SESSION: {session_id} ===\n")
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat()
    }


# Global storage for flow tasks
flow_tasks: Dict[str, asyncio.Task] = {}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    websocket_manager[session_id] = websocket
    print(f"\n=== WEBSOCKET CONNECTED: {session_id} ===\n")
    
    try:
        while True:
            data = await websocket.receive_json()
            print(f"\n=== RECEIVED: {data} ===\n")
            
            if data.get("type") == "user_message":
                message = data.get("message", "")
                
                if session_id not in flow_tasks:
                    # First message - start new flow
                    print(f"\n[WS] Starting new Prefect flow for {session_id}")
                    
                    # Create and start the flow
                    flow_task = asyncio.create_task(
                        chat_conversation_flow(session_id, message)
                    )
                    flow_tasks[session_id] = flow_task
                    
                    # Don't wait for the flow to complete (it will pause)
                    print(f"[WS] Flow started and running in background")
                    
                else:
                    # Resume existing flow
                    print(f"[WS] Flow is paused, waiting for resume signal")
                    # In a real implementation, we'd use Prefect's API to resume
                    # For now, the flow is waiting for input via pause_flow_run
                    
                    await websocket.send_json({
                        "type": "status",
                        "message": "Resume functionality requires Prefect Cloud/Server integration"
                    })
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        websocket_manager.pop(session_id, None)
        if session_id in flow_tasks:
            flow_tasks[session_id].cancel()
            flow_tasks.pop(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)