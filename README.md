# WAHA Python Client Library

A comprehensive Python client library and CLI for the [WAHA (WhatsApp HTTP API)](https://waha.devlike.pro/), auto-generated from the OpenAPI specification.

## Features

- **Sync and Async Support**: Full support for both synchronous and asynchronous operations
- **High-level OO Wrapper**: Intuitive `Client` and `Session` classes for easy interaction
- **Comprehensive CLI**: Feature-rich command-line interface built with Typer
- **Auto-generated**: Generated from WAHA's OpenAPI spec for complete API coverage
- **Type-safe**: Fully typed with attrs/dataclasses for excellent IDE support
- **Rich Output**: Beautiful CLI output with Rich library
- **Environment Variable Support**: Easy configuration via environment variables

## Installation

### Using uv (recommended)

```bash
uv pip install waha
```

### Using pip

```bash
pip install waha
```

### Development Installation

```bash
git clone https://github.com/yourusername/waha.git
cd waha
uv sync
```

## Quick Start

### Environment Variables

Configure the library using environment variables:

```bash
export WAHA_URL="http://localhost:3000"        # WAHA API base URL
export WAHA_API_KEY="your-api-key-here"        # Your API key
export WAHA_SESSION="default"                  # Default session name
```

### Python Library - Basic Usage

```python
from waha import Client

# Create a client (uses WAHA_URL and WAHA_API_KEY from environment)
client = Client()

# Get a session
session = client.session("default")

# Send a text message
session.send_text(
    body={
        "chatId": "1234567890@c.us",
        "text": "Hello from WAHA!",
        "session": "default"
    }
)

# List all groups
groups = session.get_groups()
for group in groups:
    print(f"Group: {group['name']}")
```

### CLI Usage

```bash
# List all sessions
waha sessions list

# Get session information
waha sessions get --session default

# Send a text message
waha chatting send-text \
  --session default \
  --chat-id "1234567890@c.us" \
  --text "Hello from CLI!"

# Get groups
waha groups get-groups --session default

# Send an image
waha chatting send-image \
  --session default \
  --chat-id "1234567890@c.us" \
  --caption "Check this out!" \
  --file @/path/to/image.jpg
```

## Library Usage

### Creating a Client

```python
from waha import Client

# Using environment variables
client = Client()

# Or specify directly
client = Client(
    base_url="http://localhost:3000",
    token="your-api-key"
)

# Using context manager (recommended)
with Client() as client:
    session = client.session("default")
    # ... do work
```

### Working with Sessions

```python
# Get a session
session = client.session("default")

# Get session info
info = session.get()
print(f"Session status: {info['status']}")

# Start a session
session.start()

# Stop a session
session.stop()

# Logout from session
session.logout()
```

### Sending Messages

#### Text Messages

```python
session.send_text(
    body={
        "chatId": "1234567890@c.us",
        "text": "Hello, World!",
        "session": "default"
    }
)
```

#### Images

```python
session.send_image(
    body={
        "chatId": "1234567890@c.us",
        "caption": "Check out this image!",
        "file": {
            "mimetype": "image/jpeg",
            "filename": "photo.jpg",
            "data": base64_encoded_data
        },
        "session": "default"
    }
)
```

#### Files

```python
session.send_file(
    body={
        "chatId": "1234567890@c.us",
        "caption": "Important document",
        "file": {
            "mimetype": "application/pdf",
            "filename": "document.pdf",
            "data": base64_encoded_data
        },
        "session": "default"
    }
)
```

#### Location

```python
session.send_location(
    body={
        "chatId": "1234567890@c.us",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "title": "San Francisco",
        "session": "default"
    }
)
```

### Working with Groups

```python
# List all groups
groups = session.get_groups()

# Get group participants
participants = session.get_group_participants(id="group-id@g.us")

# Create a group
session.create_group(
    body={
        "name": "My Group",
        "participants": [
            {"id": "1234567890@c.us"},
            {"id": "0987654321@c.us"}
        ]
    }
)

# Add participants
session.add_group_participants(
    id="group-id@g.us",
    body={
        "participants": [{"id": "1111111111@c.us"}]
    }
)
```

### Async Usage

All methods have async equivalents with `_async` suffix:

```python
import asyncio
from waha import Client

async def main():
    async with Client() as client:
        session = client.session("default")

        # Send message asynchronously
        result = await session.send_text_async(
            body={
                "chatId": "1234567890@c.us",
                "text": "Hello async!",
                "session": "default"
            }
        )

        # Get groups asynchronously
        groups = await session.get_groups_async()
        print(f"Found {len(groups)} groups")

asyncio.run(main())
```

### Using the Low-level API

For advanced use cases, access the auto-generated API directly:

```python
from waha import AuthenticatedClient
from waha.api import sessions, chatting

client = AuthenticatedClient(
    base_url="http://localhost:3000",
    token="your-api-key"
)

# List sessions
sessions_list = sessions.sessions_controller_list_sync(client=client)

# Send a message
result = chatting.chatting_controller_send_text_sync(
    client=client,
    session="default",
    body={
        "chatId": "1234567890@c.us",
        "text": "Hello!",
        "session": "default"
    }
)
```

## CLI Usage

### Global Options

```bash
waha --help                                    # Show help
waha --url http://localhost:3000               # Override WAHA_URL
waha --api-key your-key                        # Override WAHA_API_KEY
waha --output table                            # Change output format (json/table)
```

### Sessions Commands

```bash
# List all sessions
waha sessions list

# Create a new session
waha sessions create --name my-session --start

# Get session info
waha sessions get --session default

# Start a session
waha sessions start --session default

# Stop a session
waha sessions stop --session default

# Logout from session
waha sessions logout --session default

# Delete a session
waha sessions delete --session default

# Get authenticated account info
waha sessions get-me --session default
```

### Chatting Commands

```bash
# Send text message
waha chatting send-text \
  --session default \
  --chat-id "1234567890@c.us" \
  --text "Hello!"

# Send image
waha chatting send-image \
  --session default \
  --chat-id "1234567890@c.us" \
  --caption "Photo" \
  --file @image.jpg

# Send file
waha chatting send-file \
  --session default \
  --chat-id "1234567890@c.us" \
  --file @document.pdf

# Send location
waha chatting send-location \
  --session default \
  --chat-id "1234567890@c.us" \
  --latitude 37.7749 \
  --longitude -122.4194

# React to a message
waha chatting set-reaction \
  --session default \
  --message-id "message-id" \
  --reaction "👍"

# Get messages
waha chatting get-messages \
  --session default \
  --chat-id "1234567890@c.us" \
  --limit 100
```

### Groups Commands

```bash
# List groups
waha groups get-groups --session default

# Get group participants
waha groups get-group-participants \
  --session default \
  --id "group-id@g.us"

# Create a group
waha groups create-group \
  --session default \
  --name "My Group" \
  --participants "1234567890@c.us,0987654321@c.us"

# Add participants
waha groups add-group-participants \
  --session default \
  --id "group-id@g.us" \
  --participants "1111111111@c.us"

# Remove participants
waha groups remove-group-participants \
  --session default \
  --id "group-id@g.us" \
  --participants "1111111111@c.us"
```

### Other Commands

```bash
# Get QR code
waha auth get-qr --session default --format image

# Get profile
waha profile get-profile --session default

# Set profile name
waha profile set-profile-name --session default --name "My Name"

# Get contacts
waha contacts get-contacts --session default

# Check presence
waha presence get-presence --session default --chat-id "1234567890@c.us"

# Get screenshots (for debugging)
waha screenshot get-screenshot --session default
```

## Development

### Regenerating from OpenAPI Spec

The library is auto-generated from the WAHA OpenAPI specification. To regenerate:

1. Update `openapi.json` with the latest spec from WAHA
2. Run the generator:

```bash
uv run python -m generator.generate
```

This will:
- Generate Python client code in `src/waha/api/` and `src/waha/models/`
- Generate CLI commands in `src/waha/_cli/`
- Generate the high-level wrapper in `src/waha/wrapper.py`

### Running Examples

```bash
# Set environment variables first
export WAHA_URL="http://localhost:3000"
export WAHA_API_KEY="your-api-key"

# Run example scripts
uv run python examples/group_participants.py
```

### Project Structure

```
waha/
├── src/waha/           # Main library code
│   ├── api/            # Auto-generated API modules
│   ├── models/         # Auto-generated data models
│   ├── _cli/           # Auto-generated CLI commands
│   ├── client.py       # Low-level HTTP client
│   ├── wrapper.py      # High-level OO wrapper
│   ├── cli.py          # CLI entry point
│   ├── types.py        # Type definitions
│   └── errors.py       # Error classes
├── generator/          # Code generator
│   ├── generate.py     # Main generator script
│   └── templates/      # Jinja2 templates
├── examples/           # Example scripts
├── openapi.json        # WAHA OpenAPI spec
├── pyproject.toml      # Project configuration
└── README.md           # This file
```

## Error Handling

```python
from waha import Client
from waha.errors import WAHAError, AuthenticationError, ValidationError

client = Client()

try:
    session = client.session("default")
    session.send_text(
        body={
            "chatId": "invalid-id",
            "text": "Hello",
            "session": "default"
        }
    )
except AuthenticationError:
    print("Invalid API key")
except ValidationError as e:
    print(f"Invalid request: {e}")
except WAHAError as e:
    print(f"WAHA error: {e}")
```

## Requirements

- Python >= 3.12
- httpx >= 0.27.0
- attrs >= 24.2.0
- python-dateutil >= 2.9.0
- typer >= 0.12.0
- rich >= 13.0.0
- jinja2 >= 3.1.6 (for code generation)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `uv run pytest && uv run ruff check`
5. Submit a pull request

## Related Projects

- [WAHA](https://waha.devlike.pro/) - WhatsApp HTTP API server
- [whatsapp-web.js](https://github.com/pedroslopez/whatsapp-web.js) - WhatsApp Web API for Node.js

## Support

- Documentation: https://waha.devlike.pro/
- Issues: https://github.com/yourusername/waha/issues
- WAHA Discord: https://discord.gg/waha
