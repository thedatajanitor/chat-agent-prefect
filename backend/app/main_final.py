"""
Chat Agent Backend with Prefect Pause/Resume - Final Implementation
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from typing import Dict, Optional
from datetime import datetime
import uuid
import os
from pydantic import BaseModel

from prefect import flow, task, pause_flow_run, get_run_logger
from prefect.context import get_run_context
from prefect.input import RunInput
from prefect.client import get_client
from prefect.states import Paused
import json

# Store WebSocket connections
websocket_manager: Dict[str, WebSocket] = {}
# Store flow run IDs
flow_runs: Dict[str, str] = {}  # session_id -> flow_run_id
# Store flow tasks
flow_tasks: Dict[str, asyncio.Task] = {}  # session_id -> task

# Set Prefect API URL if provided
if os.getenv("PREFECT_API_URL"):
    import prefect
    prefect.settings.PREFECT_API_URL = os.getenv("PREFECT_API_URL")


class UserMessage(RunInput):
    """Input model for user messages during pause"""
    message: str


class WebSocketUpdate(BaseModel):
    """Model for internal WebSocket updates"""
    session_id: str
    type: str
    data: dict


async def send_to_websocket(session_id: str, msg_type: str, content: dict):
    """Helper to send messages to WebSocket if connected"""
    if session_id in websocket_manager:
        try:
            await websocket_manager[session_id].send_json({
                "type": msg_type,
                **content,
                "timestamp": datetime.now().isoformat()
            })
            print(f"[WS] Sent {msg_type} to {session_id}")
        except Exception as e:
            print(f"[WS] Error sending to {session_id}: {e}")


@task(name="process-message", log_prints=True)
async def process_message(message: str, session_id: str, interaction: int):
    """Process user message"""
    print(f"[TASK] Processing message #{interaction} for {session_id}: {message}")
    
    await send_to_websocket(session_id, "task_status", {
        "task": "process-message",
        "status": "running",
        "message": f"Processing message #{interaction}..."
    })
    
    await asyncio.sleep(2)
    
    await send_to_websocket(session_id, "task_status", {
        "task": "process-message",
        "status": "completed",
        "message": "Message processed"
    })
    
    return {
        "message": message,
        "word_count": len(message.split()),
        "interaction": interaction,
        "processed_at": datetime.now().isoformat()
    }


@task(name="analyze-sentiment", log_prints=True)
async def analyze_sentiment(context: dict, session_id: str):
    """Analyze sentiment"""
    print(f"[TASK] Analyzing sentiment for {session_id}")
    
    await send_to_websocket(session_id, "task_status", {
        "task": "analyze-sentiment",
        "status": "running",
        "message": "Analyzing sentiment..."
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
    
    await send_to_websocket(session_id, "task_status", {
        "task": "analyze-sentiment",
        "status": "completed",
        "message": f"Sentiment: {sentiment}"
    })
    
    print(f"[TASK] Sentiment detected: {sentiment}")
    return sentiment


@task(name="generate-response", log_prints=True)
async def generate_response(context: dict, sentiment: str, session_id: str):
    """Generate response"""
    print(f"[TASK] Generating response for {session_id}")
    
    await send_to_websocket(session_id, "task_status", {
        "task": "generate-response",
        "status": "running",
        "message": "Generating response..."
    })
    
    await asyncio.sleep(2)
    
    interaction = context["interaction"]
    message = context["message"]
    
    if interaction == 1:
        response = f"Hello! I received your first message: '{message}' ({sentiment} sentiment). The flow is now paused. Send another message to resume!"
    elif interaction == 2:
        response = f"Great! The flow resumed successfully. Your message '{message}' shows {sentiment} sentiment. This is interaction #{interaction}."
    else:
        response = f"Interaction #{interaction}: I processed '{message}' with {sentiment} sentiment. The flow continues to pause/resume!"
    
    await send_to_websocket(session_id, "task_status", {
        "task": "generate-response",
        "status": "completed",
        "message": "Response generated"
    })
    
    print(f"[TASK] Generated response: {response}")
    return response


@flow(name="chat-pause-resume-flow", log_prints=True, persist_result=True)
async def chat_pause_resume_flow(session_id: str, initial_message: str):
    """
    Main chat flow that pauses between interactions
    """
    logger = get_run_logger()
    logger.info(f"Starting conversation flow for {session_id}")
    logger.info(f"Initial message: {initial_message}")
    
    # Get the flow run context to access flow run ID
    context = get_run_context()
    if context and context.flow_run:
        flow_run_id = str(context.flow_run.id)
        flow_runs[session_id] = flow_run_id
        logger.info(f"Flow run ID: {flow_run_id}")
        
        await send_to_websocket(session_id, "flow_status", {
            "status": "started",
            "message": "Chat flow started",
            "flow_run_id": flow_run_id
        })
    
    conversation_history = []
    interaction = 0
    message = initial_message
    
    while interaction < 10:  # Safety limit
        interaction += 1
        logger.info(f"\n=== Interaction {interaction} ===")
        
        await send_to_websocket(session_id, "flow_status", {
            "status": "processing",
            "message": f"Processing interaction {interaction}",
            "interaction": interaction
        })
        
        # Execute tasks
        context_data = await process_message(message, session_id, interaction)
        sentiment = await analyze_sentiment(context_data, session_id)
        response = await generate_response(context_data, sentiment, session_id)
        
        # Send the agent response
        await send_to_websocket(session_id, "agent_message", {
            "message": response,
            "interaction": interaction,
            "sentiment": sentiment
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
            logger.info("User requested exit")
            await send_to_websocket(session_id, "flow_status", {
                "status": "completed",
                "message": "Conversation ended. Thank you!"
            })
            break
        
        # Notify that we're pausing
        logger.info("Pausing flow to wait for user input...")
        await send_to_websocket(session_id, "flow_status", {
            "status": "paused",
            "message": "Flow paused. Send a message to resume...",
            "interaction": interaction
        })
        
        # PAUSE THE FLOW AND WAIT FOR INPUT
        user_input = await pause_flow_run(
            wait_for_input=UserMessage,
            timeout=600  # 10 minute timeout
        )
        
        if not user_input:
            logger.info("Timeout waiting for user input")
            await send_to_websocket(session_id, "flow_status", {
                "status": "timeout",
                "message": "Flow timed out waiting for input"
            })
            break
        
        # Flow resumes here with new message
        message = user_input.message
        logger.info(f"Flow resumed with message: {message}")
        
        await send_to_websocket(session_id, "flow_status", {
            "status": "resumed",
            "message": "Flow resumed!",
            "interaction": interaction + 1
        })
    
    logger.info(f"Conversation flow completed for {session_id}")
    return {
        "session_id": session_id,
        "total_interactions": interaction,
        "history": conversation_history,
        "completed_at": datetime.now().isoformat()
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Chat Agent with Prefect Pause/Resume...")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Chat Agent with Prefect Pause/Resume",
    version="4.0.0",
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
    """Health check endpoint"""
    prefect_connected = False
    try:
        async with get_client() as client:
            await client.read_flow_runs(limit=1)
            prefect_connected = True
    except:
        pass
    
    return {
        "status": "healthy",
        "active_sessions": len(websocket_manager),
        "active_flows": len(flow_runs),
        "prefect_connected": prefect_connected
    }


@app.post("/api/chat/start")
async def start_chat_session():
    """Start a new chat session"""
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    print(f"\n=== NEW SESSION: {session_id} ===\n")
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat()
    }


@app.post("/api/internal/websocket-update")
async def internal_websocket_update(update: WebSocketUpdate):
    """Internal endpoint for flows to send WebSocket updates"""
    if update.session_id in websocket_manager:
        await send_to_websocket(update.session_id, update.type, update.data)
        return {"status": "sent"}
    return {"status": "no_connection"}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    websocket_manager[session_id] = websocket
    print(f"\n=== WEBSOCKET CONNECTED: {session_id} ===\n")
    
    try:
        while True:
            data = await websocket.receive_json()
            print(f"\n=== RECEIVED: {json.dumps(data, indent=2)} ===\n")
            
            if data.get("type") == "user_message":
                message = data.get("message", "")
                
                if session_id not in flow_runs:
                    # First message - start new flow
                    print(f"[WS] Starting new Prefect flow for {session_id}")
                    print(f"[WS] Initial message: {message}")
                    
                    try:
                        # Create and start the flow
                        flow_task = asyncio.create_task(
                            chat_pause_resume_flow(session_id, message)
                        )
                        flow_tasks[session_id] = flow_task
                        
                        print(f"[WS] Flow started in background")
                        
                        # The flow will communicate via WebSocket
                        
                    except Exception as e:
                        print(f"[WS] Error starting flow: {e}")
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Failed to start flow: {str(e)}"
                        })
                
                else:
                    # Resume existing flow
                    flow_run_id = flow_runs[session_id]
                    print(f"[WS] Attempting to resume flow {flow_run_id}")
                    print(f"[WS] Resume message: {message}")
                    
                    try:
                        async with get_client() as client:
                            # Resume the paused flow with the new message
                            flow_run = await client.read_flow_run(flow_run_id)
                            
                            if flow_run.state.is_paused():
                                print(f"[WS] Flow is paused, resuming with message: {message}")
                                await client.resume_flow_run(
                                    flow_run_id,
                                    run_input={"message": message}
                                )
                                print(f"[WS] Resume command sent successfully")
                            else:
                                print(f"[WS] Flow is in state: {flow_run.state.name}")
                                await websocket.send_json({
                                    "type": "status",
                                    "message": f"Flow is {flow_run.state.name}, cannot resume"
                                })
                            
                    except Exception as e:
                        print(f"[WS] Error resuming flow: {e}")
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Failed to resume flow: {str(e)}"
                        })
                
    except WebSocketDisconnect:
        print(f"[WS] WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"[WS] WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        websocket_manager.pop(session_id, None)
        # Clean up but don't cancel the flow task - let it complete or timeout
        print(f"[WS] Cleaned up connection for {session_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)