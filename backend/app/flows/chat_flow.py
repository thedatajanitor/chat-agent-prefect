"""
Prefect flow for chat conversations with pause/resume functionality
"""
from prefect import flow, task, pause_flow_run, get_run_logger
from prefect.context import get_run_context
from prefect.input import RunInput
import asyncio
from datetime import datetime
from typing import Dict, Optional


class UserMessage(RunInput):
    """Input model for user messages during pause"""
    message: str


async def send_to_websocket(session_id: str, msg_type: str, content: dict):
    """Helper to send messages to WebSocket if connected"""
    # Import here to avoid circular dependency
    from app.main import websocket_manager
    
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
async def chat_pause_resume_flow(session_id: str, initial_message: str, flow_runs_dict: Dict[str, str]):
    """
    Main chat flow that pauses between interactions
    
    Args:
        session_id: Unique session identifier
        initial_message: First message from user
        flow_runs_dict: Dictionary to store flow run IDs
    """
    logger = get_run_logger()
    logger.info(f"Starting conversation flow for {session_id}")
    logger.info(f"Initial message: {initial_message}")
    
    # Get the flow run context to access flow run ID
    context = get_run_context()
    if context and context.flow_run:
        flow_run_id = str(context.flow_run.id)
        flow_runs_dict[session_id] = flow_run_id
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