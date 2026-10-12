"""Ingestion reader for authorized personal information sources.

Reads local email, messaging, and calendar fixtures while strictly adhering
to user privacy preferences and source authorization switches.
"""

import json
import os
from datetime import datetime
from typing import List
from proactive_pet.models import SourceItem


class LocalSourceReader:
    """Reads authorized data from local fixtures and connected endpoints."""

    def __init__(self, fixtures_dir: str):
        self.fixtures_dir = fixtures_dir
        self.authorized_sources = {
            "email": True,
            "message": True,
            "calendar": True
        }

    def set_source_authorization(self, source_type: str, enabled: bool):
        """Allows user to inspect sources and revoke/grant access dynamically."""
        self.authorized_sources[source_type] = enabled

    def load_all_items(self) -> List[SourceItem]:
        """Loads and parses all authorized incoming items."""
        items: List[SourceItem] = []

        if self.authorized_sources.get("email"):
            items.extend(self._load_emails())

        if self.authorized_sources.get("message"):
            items.extend(self._load_messages())

        if self.authorized_sources.get("calendar"):
            items.extend(self._load_calendars())

        return items

    def _load_emails(self) -> List[SourceItem]:
        filepath = os.path.join(self.fixtures_dir, "email_samples.json")
        if not os.path.exists(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = []
        for d in data:
            if not d.get("is_authorized", True):
                continue
            ts = datetime.fromisoformat(d.get("received_at", datetime.now().isoformat()))
            results.append(
                SourceItem(
                    id=d["id"],
                    source_type="email",
                    sender_or_owner=d.get("sender", "unknown"),
                    content=f"Subject: {d.get('subject', '')}\n{d.get('content', '')}",
                    timestamp=ts,
                    is_authorized=True,
                    metadata={"subject": d.get("subject", "")}
                )
            )
        return results

    def _load_messages(self) -> List[SourceItem]:
        filepath = os.path.join(self.fixtures_dir, "message_samples.json")
        if not os.path.exists(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = []
        for d in data:
            if not d.get("is_authorized", True):
                continue
            ts = datetime.fromisoformat(d.get("received_at", datetime.now().isoformat()))
            results.append(
                SourceItem(
                    id=d["id"],
                    source_type="message",
                    sender_or_owner=d.get("sender", "unknown"),
                    content=d.get("content", ""),
                    timestamp=ts,
                    is_authorized=True
                )
            )
        return results

    def _load_calendars(self) -> List[SourceItem]:
        filepath = os.path.join(self.fixtures_dir, "calendar_samples.json")
        if not os.path.exists(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = []
        for d in data:
            if not d.get("is_authorized", True):
                continue
            ts = datetime.fromisoformat(d.get("start_time", datetime.now().isoformat()))
            body = f"Title: {d.get('title', '')}\nLocation: {d.get('location', '')}\nNotes: {d.get('notes', '')}"
            results.append(
                SourceItem(
                    id=d["id"],
                    source_type="calendar",
                    sender_or_owner="Local Calendar",
                    content=body,
                    timestamp=ts,
                    is_authorized=True,
                    metadata={
                        "title": d.get("title", ""),
                        "start_time": d.get("start_time", ""),
                        "end_time": d.get("end_time", ""),
                        "location": d.get("location", "")
                    }
                )
            )
        return results
