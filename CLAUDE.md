# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a chat agent project that demonstrates Prefect's pause/resume functionality for orchestrating conversational AI workflows. The system consists of:
- **Frontend**: Assistant UI (Next.js/React) for the chat interface
- **Backend**: FastAPI server handling WebSocket connections and flow management
- **Orchestration**: Prefect flows that pause after each agent response to await user input
- **AI Agent**: Marvin-powered chat agent for generating responses

## Architecture

### Key Components

1. **WebSocket Communication**: Real-time bidirectional communication between frontend and backend
2. **Prefect Flow Management**: Each chat session creates a Prefect flow that:
   - Starts when the user sends their first message
   - Processes the message through various tasks
   - Generates an agent response
   - Pauses the flow to wait for the next user input
   - Resumes when new input arrives
3. **Docker Compose Setup**: All services run in containers for easy deployment

### Project Structure
```
chat-agent-prefect/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── flows/        # Prefect flow definitions
│   │   ├── agents/       # Marvin AI agent logic
│   │   └── main.py       # FastAPI application
│   └── Dockerfile
├── frontend/
│   ├── app/              # Next.js app directory
│   │   ├── hooks/        # React hooks for chat
│   │   └── page.tsx      # Main chat interface
│   └── Dockerfile
├── docker-compose.yml    # Container orchestration
├── pyproject.toml        # Python dependencies
└── .env                  # Environment variables
```

## Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ with `uv` package manager
- Node.js 20+ (for local frontend development)

### Environment Variables
Copy `.env.example` to `.env` and configure:
- `OPENAI_API_KEY`: Required for Marvin AI functionality
- `PREFECT_API_URL`: Prefect server URL (default: http://localhost:4200/api)

### Python Package Management
- Use `uv` as the Python package manager
- Install dependencies: `uv sync`
- Add new dependencies: `uv add <package>`

## Common Commands

### Development
- `docker-compose up`: Start all services
- `docker-compose up --build`: Rebuild and start services
- `docker-compose logs -f backend`: View backend logs
- `docker-compose logs -f prefect`: View Prefect server logs
- `docker-compose down`: Stop and remove containers

### Backend Development (Local)
- `uv run uvicorn app.main:app --reload`: Run FastAPI locally
- `uv run python -m app.flows.chat_flow`: Test flow locally

### Frontend Development (Local)
- `cd frontend && npm install`: Install dependencies
- `cd frontend && npm run dev`: Start development server

### Prefect Commands
- Access Prefect UI: http://localhost:4200
- View flow runs and logs in the Prefect UI

## Key Implementation Details

### Current Implementation (MVP)
The current implementation simulates Prefect flow execution to demonstrate the concept:
1. User sends first message → "Starting new Prefect flow..."
2. Three tasks execute sequentially with status updates:
   - Task 1: Process Message (2s)
   - Task 2: Analyze Sentiment (1.5s)  
   - Task 3: Generate Response (2s)
3. Agent sends response and flow "pauses"
4. User sends next message → "Resuming Prefect flow..."
5. Process repeats with context from previous interactions

### Production Implementation (main_prefect3.py)
For production use with real Prefect:
1. Use `pause_flow_run(wait_for_input=UserMessage)` for typed input
2. Use `run_deployment()` for non-blocking flow execution
3. Resume with `client.resume_flow_run(flow_run_id, run_input={...})`
4. Monitor flow state via Prefect API

### WebSocket Protocol
```typescript
// User message
{
  "type": "user_message",
  "message": "Hello, agent!"
}

// Agent response
{
  "type": "agent_message",
  "message": "Hello! How can I help you?",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Marvin Agent Integration
The `ChatAgent` class uses Marvin's `@ai_fn` decorators to:
- Analyze user messages for intent and context
- Generate contextually appropriate responses
- Maintain conversation history
- Detect when to end conversations

## Testing

### Manual Testing Flow
1. Start services: `docker-compose up`
2. Open frontend: http://localhost:3000
3. Send a message in the chat interface
4. Observe in Prefect UI (http://localhost:4200):
   - Flow run starts
   - Tasks execute
   - Flow pauses after response
5. Send another message
6. Observe flow resume and continue

### Debugging Tips
- Check WebSocket connection in browser DevTools
- Monitor Prefect flow runs in the UI
- View container logs for errors
- Ensure all environment variables are set correctly