# Chat Agent with Prefect Orchestration

This project demonstrates a chat interface backed by Prefect flow orchestration, showcasing pause/resume functionality and real-time task execution visibility.

## Architecture

- **Frontend**: Next.js/React chat interface with WebSocket support
- **Backend**: FastAPI with WebSocket endpoints and Prefect flow integration
- **Orchestration**: Prefect 3 for workflow management with pause/resume capabilities
- **Infrastructure**: Docker Compose for easy deployment

## Features

- Real-time chat interface with WebSocket communication
- Prefect flows that execute on each message
- Visual task execution progress (process → analyze → respond)
- Multiple task execution with configurable delays
- Session management and flow state tracking
- Full observability through Prefect dashboard

## Quick Start

1. Start all services:
```bash
docker-compose up -d
```

2. Access the services:
- Chat Interface: http://localhost:3000
- FastAPI Docs: http://localhost:8000/docs
- Prefect Dashboard: http://localhost:4200

3. Start chatting! Each message triggers a Prefect flow with three tasks:
   - **Process Message**: Analyzes the message content
   - **Analyze Sentiment**: Determines message sentiment
   - **Generate Response**: Creates an appropriate response

## Implementation Details

### Current Implementation (main_final.py)

The current implementation provides true Prefect pause/resume functionality:
- Each chat session creates a single Prefect flow that persists across messages
- The flow pauses after processing each message using `pause_flow_run()`
- When a new message arrives, the flow resumes with the input using Prefect's API
- Full task visibility and orchestration through Prefect dashboard
- WebSocket updates sent directly from flow tasks

### Simple Implementation (main_simple.py)

The current implementation runs a new Prefect flow for each message. This demonstrates:
- Real Prefect flow execution (not simulation)
- Task orchestration with proper logging
- WebSocket integration for real-time updates
- Session-based flow management

Each message triggers a complete flow run visible in the Prefect dashboard.

### Advanced Implementation (main.py)

The advanced implementation (available but not active) includes:
- True pause/resume functionality using `pause_flow_run()`
- Persistent flow state across messages
- Typed input collection during pause
- Conversation history tracking

To switch between implementations, update `docker-compose.yml`:
```yaml
# For pause/resume (current):
command: uv run uvicorn app.main_final:app --host 0.0.0.0 --port 8000 --reload

# For simple flow-per-message:
command: uv run uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 --reload
```

Note: Full pause/resume requires Prefect Cloud or a configured Prefect Server with proper state persistence.

## Project Structure

```
chat-agent-prefect/
├── backend/
│   └── app/
│       ├── main_final.py     # Current: True pause/resume flows
│       ├── main_simple.py    # Alternative: Simple flow-per-message
│       └── flows_pause_resume.py  # Flow definitions
├── frontend/
│   └── app/
│       └── simple-chat.tsx   # React chat component
├── docker-compose.yml        # Service orchestration
├── test_pause_resume.py      # Test script for pause/resume
└── README.md
```

## Development

Both frontend and backend support hot reloading:
- Frontend changes reflect immediately
- Backend changes trigger automatic restart
- Prefect flows are re-registered on backend restart

## Monitoring

View flow execution in the Prefect dashboard:
1. Navigate to http://localhost:4200
2. Click on "Flow Runs" to see all executions
3. Click on individual runs to see task details

## Testing Pause/Resume

To test the pause/resume functionality:

1. Using the UI:
   - Open http://localhost:3000
   - Send a message and watch the flow execute
   - Notice the flow pauses after responding
   - Send another message to resume the same flow

2. Using the test script:
   ```bash
   python test_pause_resume.py
   ```

3. Monitor in Prefect Dashboard:
   - Open http://localhost:4200
   - Watch the flow pause and resume states
   - See task execution details

## Notes

- Each chat session creates a single persistent flow
- Flows pause between messages using Prefect's `pause_flow_run()`
- Messages resume the flow with typed input via Prefect's API
- The system demonstrates real-world human-in-the-loop workflows
- Flow state is maintained by Prefect Server with PostgreSQL backend