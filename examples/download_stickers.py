#!/usr/bin/env python3
"""Download all stickers from specific WhatsApp groups.

This example demonstrates how to:
1. Connect to a WAHA WhatsApp API instance
2. Find groups by name
3. Fetch messages from groups
4. Filter and download stickers (deduplicated)

Environment Variables:
    WAHA_URL: The base URL for the WAHA API (default: http://localhost:3000)
    WAHA_API_KEY: The API key for authentication
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import httpx

from waha import Client, Group, Message

SESSION_ID = "e2d2542a-e855-4254-f460-71866f6525c2"
TARGET_GROUPS = [
    "הפרלמנט - הקבוצה הרשמית",
    "שים לי את זה בסלון",
]
OUTPUT_DIR = Path("stickers")
MESSAGES_LIMIT = 10000


def is_sticker(msg: Message) -> bool:
    """Check if a message is a sticker."""
    if not msg.has_media:
        return False

    media = msg.media
    if not media:
        return False

    mimetype = media.mimetype or ""
    return "webp" in mimetype.lower()


def get_sticker_url(msg: Message) -> str | None:
    """Extract the sticker URL from a message."""
    media = msg.media
    if media and media.url:
        return media.url
    return msg.media_url or None


def get_sticker_id(msg: Message) -> str | None:
    """Get a unique identifier for a sticker (for deduplication)."""
    url = get_sticker_url(msg)
    if url:
        # Use URL hash as ID since the same sticker will have the same media URL
        return hashlib.md5(url.encode()).hexdigest()[:16]
    return None


def find_groups_by_name(groups: list[Group], names: list[str]) -> list[Group]:
    """Find groups matching any of the given names."""
    found = []
    for group in groups:
        if group.name in names:
            found.append(group)
    return found


def download_sticker(url: str, output_path: Path) -> bool:
    """Download a sticker from URL to file."""
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        output_path.write_bytes(response.content)
        return True
    except Exception as e:
        print(f"  Failed to download: {e}")
        return False


def main() -> int:
    """Main function to download stickers from specified groups."""
    print("Connecting to WAHA API...")
    client = Client()
    session = client.session(SESSION_ID)

    print(f"Fetching groups for session '{SESSION_ID}'...")
    groups = session.groups.get_groups()

    if not groups:
        print("No groups found in this session.")
        return 1

    print(f"Found {len(groups)} group(s)")

    # Find target groups
    target_groups = find_groups_by_name(groups, TARGET_GROUPS)
    if not target_groups:
        print(f"\nCould not find any of the target groups:")
        for name in TARGET_GROUPS:
            print(f"  - {name}")
        print("\nAvailable groups:")
        for group in groups:
            print(f"  - {group.name}")
        return 1

    print(f"\nFound {len(target_groups)} target group(s):")
    for group in target_groups:
        print(f"  - {group.name}")

    # Collect stickers from all target groups
    stickers: dict[str, tuple[Message, str]] = {}  # id -> (message, url)

    for group in target_groups:
        if not group.jid:
            print(f"\nSkipping group {group.name}: no JID")
            continue

        print(f"\nFetching messages from '{group.name}'...")
        try:
            messages = session.chatting.get_messages(
                chat_id=group.jid,
                limit=MESSAGES_LIMIT,
                download_media=True,
            )
        except Exception as e:
            print(f"  Error fetching messages: {e}")
            continue

        print(f"  Found {len(messages)} messages")

        # Filter stickers
        group_stickers = 0
        expired_stickers = 0
        for msg in messages:
            if is_sticker(msg):
                sticker_id = get_sticker_id(msg)
                sticker_url = get_sticker_url(msg)
                if sticker_url and sticker_id and sticker_id not in stickers:
                    stickers[sticker_id] = (msg, sticker_url)
                    group_stickers += 1
                elif not sticker_url:
                    expired_stickers += 1

        print(f"  Found {group_stickers} unique stickers")
        if expired_stickers:
            print(f"  ({expired_stickers} stickers with expired/unavailable media)")

    print(f"\nTotal unique stickers across all groups: {len(stickers)}")

    if not stickers:
        print("No stickers to download.")
        return 0

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"\nDownloading stickers to '{OUTPUT_DIR}/'...")

    # Download stickers
    downloaded = 0
    for sticker_id, (msg, url) in stickers.items():
        output_path = OUTPUT_DIR / f"{sticker_id}.webp"
        if output_path.exists():
            print(f"  {sticker_id}.webp (already exists)")
            downloaded += 1
            continue

        print(f"  {sticker_id}.webp ...", end=" ", flush=True)
        if download_sticker(url, output_path):
            print("OK")
            downloaded += 1
        else:
            print("FAILED")

    print(f"\nDownloaded {downloaded}/{len(stickers)} stickers to '{OUTPUT_DIR}/'")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        print("\nMake sure you have set WAHA_URL and WAHA_API_KEY environment variables.")
        sys.exit(1)
