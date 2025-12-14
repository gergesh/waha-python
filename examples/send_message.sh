#!/bin/bash
# Send a WhatsApp message using the WAHA CLI
#
# Usage:
#   ./send_message.sh <chat_id> <message>
#
# Arguments:
#   chat_id  - The WhatsApp chat ID (e.g., "1234567890@c.us" for individual, "1234567890@g.us" for group)
#   message  - The message text to send
#
# Environment Variables:
#   WAHA_URL      - The base URL for the WAHA API (default: http://localhost:3000)
#   WAHA_API_KEY  - The API key for authentication (required)
#   WAHA_SESSION  - The session name to use (default: default)
#
# Examples:
#   ./send_message.sh "1234567890@c.us" "Hello, World!"
#   ./send_message.sh "1234567890@g.us" "Message to a group"

set -e

# Check if arguments are provided
if [ $# -lt 2 ]; then
    echo "Error: Missing required arguments"
    echo ""
    echo "Usage: $0 <chat_id> <message>"
    echo ""
    echo "Arguments:"
    echo "  chat_id  - The WhatsApp chat ID (e.g., '1234567890@c.us' for individual, '1234567890@g.us' for group)"
    echo "  message  - The message text to send"
    echo ""
    echo "Environment Variables:"
    echo "  WAHA_URL      - The base URL for the WAHA API (default: http://localhost:3000)"
    echo "  WAHA_API_KEY  - The API key for authentication (required)"
    echo "  WAHA_SESSION  - The session name to use (default: default)"
    echo ""
    echo "Examples:"
    echo "  $0 '1234567890@c.us' 'Hello, World!'"
    echo "  $0 '1234567890@g.us' 'Message to a group'"
    exit 1
fi

# Get arguments
CHAT_ID="$1"
MESSAGE="$2"

# Get session from environment or use default
SESSION="${WAHA_SESSION:-default}"

# Check if WAHA_API_KEY is set
if [ -z "$WAHA_API_KEY" ]; then
    echo "Error: WAHA_API_KEY environment variable is not set"
    exit 1
fi

# Build JSON body
BODY=$(cat <<EOF
{
  "chatId": "$CHAT_ID",
  "text": "$MESSAGE",
  "session": "$SESSION"
}
EOF
)

# Send message using WAHA CLI
echo "Sending message to $CHAT_ID..."
waha chatting send-text --body "$BODY"

echo "Message sent successfully!"
