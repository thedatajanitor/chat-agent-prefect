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

### How Status Updates Work

**Status updates come DIRECTLY from the Prefect flow itself:**
- Each Prefect task calls `send_to_websocket()` to send real-time updates
- The flow has direct access to the WebSocket connections
- No polling or external tracking - updates are pushed from within the flow execution

### Implementation (main.py)

The implementation provides true Prefect pause/resume functionality:
- Each chat session creates a single Prefect flow that persists across messages
- The flow pauses after processing each message using `pause_flow_run()`
- When a new message arrives, the flow resumes with the input using Prefect's API
- Full task visibility and orchestration through Prefect dashboard
- WebSocket updates sent directly from flow tasks


## Project Structure

```
chat-agent-prefect/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI backend
│   │   └── flows/
│   │       ├── __init__.py
│   │       └── chat_flow.py  # Prefect flow with tasks
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   └── simple-chat.tsx   # React chat component
│   ├── Dockerfile
│   ├── package.json
│   └── ...
├── docker-compose.yml        # Service orchestration
├── test_pause_resume.py      # Test script
├── README.md
└── .gitignore
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
- Status updates are sent directly from Prefect flow tasks to the frontend via WebSocket