# Agent Context Components

This directory contains React components for the Agent Context application.

## Structure

```
src/components/
├── pages/           # Page-level components
│   ├── AgentChatPage.tsx    # Main chat interface
│   ├── DemoPage.tsx         # Demo page for testing
│   └── index.ts             # Exports
├── ui/              # Reusable UI components
│   ├── Button.tsx           # Button component
│   ├── Input.tsx            # Input field component
│   ├── Textarea.tsx         # Textarea component
│   ├── Select.tsx           # Select dropdown component
│   ├── Card.tsx             # Card container component
│   ├── Badge.tsx            # Badge component
│   └── index.ts             # Exports
└── README.md        # This file
```

## Usage

### AgentChatPage

The main page component that provides:

- **Session Management**: List and select sessions from real API
- **Chat Interface**: Send messages and view responses
- **Context Management**: Add context to sessions using PUT requests

```tsx
import { AgentChatPage } from '@/components/pages';

function App() {
  return <AgentChatPage />;
}
```

### UI Components

All UI components are available from the ui directory:

```tsx
import { Button, Input, Textarea, Select, Card, Badge } from '@/components/ui';

// Example usage
<Card className="p-4">
  <Input placeholder="Enter text..." />
  <Button variant="outline" size="sm">Click me</Button>
</Card>
```

## Features

### Session Management
- **Real API Integration**: Fetches sessions from `/api/agent/sessions`
- **Session Context**: Loads context summary for each session
- **Session Count**: Shows total number of active sessions
- **Refresh Button**: Manually reload sessions
- **Create New Sessions**: Create new sessions via API
- **Session Selection**: Switch between sessions

### Chat Functionality
- Real-time messaging with the agent
- Message history display
- Loading states and error handling
- Auto-scroll to latest messages

### Context Management
- Add context using PUT requests
- Support for different data types (string, number, boolean, object)
- Context form with validation
- Real-time context updates

## API Integration

The components integrate with the backend API at `http://localhost:5001/api`:

- `GET /api/agent/sessions` - Get list of active sessions
- `POST /api/agent` - Create new session
- `GET /api/agent/chat?session_id={id}` - Get chat messages for a session
- `POST /api/agent/chat` - Send chat message
- `GET /api/agent/context` - Get session context
- `PUT /api/agent/context` - Add context to session

## Styling

All components use Tailwind CSS for styling and are fully responsive.

## Development

To use these components:

1. Ensure the backend API is running on port 5001
2. Import the components as needed
3. The components will automatically handle API communication and state management
4. Sessions are loaded automatically on component mount
5. Use the refresh button to reload sessions manually 