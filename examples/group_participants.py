#!/usr/bin/env python3
"""Get all participants for all groups in a WhatsApp session.

This example demonstrates how to:
1. Connect to a WAHA WhatsApp API instance
2. List all groups in a session
3. Retrieve participants for each group

Environment Variables:
    WAHA_URL: The base URL for the WAHA API (default: http://localhost:3000)
    WAHA_API_KEY: The API key for authentication
    WAHA_SESSION: The session name (default: default)
"""

from __future__ import annotations

import os
import sys

from waha import Client, Group, Participant


def print_group_info(group: Group, participants: list[Participant]) -> None:
    """Print formatted information about a group and its participants."""
    print(f"\n{'='*80}")
    print(f"Group: {group.name}")
    print(f"ID: {group.jid}")
    print(f"Topic: {group.topic or '(none)'}")
    print(f"Participants: {len(participants)}")
    print(f"{'-'*80}")

    for i, participant in enumerate(participants, 1):
        print(f"{i:3d}. {participant.id:40s} [{participant.role}]")


def main() -> int:
    """Main function to get and display group participants."""
    try:
        print("Connecting to WAHA API...")
        client = Client()
        session_name = os.environ.get("WAHA_SESSION", "default")
        session = client.session(session_name)

        print(f"Fetching groups for session '{session_name}'...")
        groups = session.groups.get_groups()

        if not groups:
            print("\nNo groups found in this session.")
            return 0

        print(f"\nFound {len(groups)} group(s)")

        for group in groups:
            try:
                if not group.jid:
                    print(f"\nSkipping group {group.name}: no JID")
                    continue
                participants = session.groups.get_participants(id=group.jid)
                print_group_info(group, participants)
            except Exception as e:
                print(f"\nError getting participants for group {group.name}: {e}")
                continue

        print(f"\n{'='*80}\n")
        return 0

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 1

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        print("\nMake sure you have set WAHA_URL and WAHA_API_KEY environment variables.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
