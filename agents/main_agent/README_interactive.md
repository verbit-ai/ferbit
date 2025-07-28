# Interactive Main Agent Client

An interactive command-line client for the AI Agent Task Manager that provides streaming responses and continuous conversation capabilities.

## Features

- 🌊 **Streaming Responses**: Real-time text streaming as the agent processes your query
- 🔄 **Iterative Workflow**: Follows the decompose → search → combine → validate workflow
- 💬 **Continuous Conversation**: Ask multiple questions in the same session
- 🎯 **Agent Coordination**: Automatically coordinates with expert_agent and search_agent
- ⚡ **Real-time Feedback**: See responses as they're generated

## Usage

### Start the Interactive Client

```bash
python interactive_client.py
```

### Example Session

```
🤖 Interactive AI Agent Task Manager Client
============================================================
📝 Type your questions and get streaming responses
💡 Commands: 'quit', 'exit', or Ctrl+C to stop
🔄 The agent will use its iterative workflow: decompose → search → combine → validate
============================================================

🔌 Connecting to main agent...
✅ Connected to: AI Agent Task Manager
📋 A manager of a team of AI agents that assigns tasks based on their capabilities...

🗣️  Your question: Tell me about the accident case involving Manning and Frederick

🌊 Response #1:
📥 I'll help you find information about the accident case involving Manning and Frederick. Let me break this down into specific searches to get comprehensive information.

[Agent processes through its workflow...]

────────────────────────────────────────────────────────────
📊 Response completed (3 chunks, 1247 characters)

🗣️  Ask another question (or 'quit'): What evidence exists about the incident?

🌊 Response #2:
📥 Let me search for specific evidence related to the Manning-Frederick incident...

[Agent continues with new query...]
```

## Commands

- **Regular Questions**: Type any question and press Enter
- **Exit Commands**: Type `quit`, `exit`, or `q` to end the session
- **Keyboard Interrupt**: Press `Ctrl+C` to stop at any time

## How It Works

1. **Connection**: Connects to the main agent at `http://localhost:9111`
2. **Streaming**: Uses A2A protocol streaming for real-time responses
3. **Workflow**: The main agent follows its iterative process:
   - Decomposes complex queries using expert_agent
   - Searches for information using search_agent
   - Combines and validates results
   - Provides comprehensive responses

## Prerequisites

- Main agent server running on port 9111
- Expert agent running on port 8003
- Search agent running on port 8001

## Troubleshooting

### Connection Failed
```
❌ Failed to connect to main agent at http://localhost:9111
```
**Solution**: Make sure the main agent server is running:
```bash
python a2a_server.py
```

### No Response Received
If you see "(No response received)", the agent may be having issues communicating with other agents. Check that all required agents are running.

### Interrupted Session
Press `Ctrl+C` or type `quit` to gracefully exit the session.

## Technical Details

- Uses async/await for non-blocking I/O
- Implements proper error handling and recovery
- Supports graceful shutdown
- Minimal logging for clean interactive experience
- Real-time character streaming for immediate feedback