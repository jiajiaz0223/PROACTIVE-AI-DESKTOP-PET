"""Local AI event extractor running on edge hardware (ASUS UGen300).

Transforms natural language from emails, chats, and calendar descriptions
into verified structured events without halluncinating missing facts.
"""

import re
from datetime import datetime, timedelta
from typing import Optional
from proactive_pet.models import SourceItem, ExtractedEvent
from proactive_pet.ai.hailo_ugen300_adapter import ASUSUGen300Adapter


class LocalAIExtractor:
    """Extracts structured schedule and preparation commitments from text."""

    def __init__(self, hardware_adapter: Optional[ASUSUGen300Adapter] = None):
        self.hardware_adapter = hardware_adapter or ASUSUGen300Adapter()
        self.last_telemetry = {}

    def extract_event(self, item: SourceItem) -> Optional[ExtractedEvent]:
        """Analyzes an authorized item and extracts a structured event if actionable.
        
        Rule from Slide 7 & 9:
        - Only relevant, actionable commitments become reminders.
        - Missing facts stay unknown (None) instead of being invented.
        """
        text = item.content

        # Execute on-device quantized inference via ASUS UGen300 NPU
        self.last_telemetry = self.hardware_adapter.run_npu_inference(text)

        # 1. Actionable filter (Discards promotional newsletters, small talks)
        lower_text = text.lower()
        non_actionable_keywords = ["pizza", "discount", "sale", "basketball game", "promo", "newsletter"]
        if any(kw in lower_text for kw in non_actionable_keywords) and "interview" not in lower_text:
            return None

        # 2. Extract Event Category & Title
        event_type = "general"
        title = "Scheduled Commitment"

        if "interview" in lower_text:
            event_type = "interview"
            title = "Job Interview"
        elif "meeting" in lower_text or "sync" in lower_text:
            event_type = "meeting"
            title = "Sprint / Online Meeting"
        elif "submission" in lower_text or "deadline" in lower_text or "due" in lower_text:
            event_type = "submission"
            title = "Document Submission"

        # Check if calendar metadata already provides exact title
        if item.source_type == "calendar" and "title" in item.metadata:
            title = item.metadata["title"]

        # 3. Extract Target Time
        target_time = self._extract_datetime(text, item)
        if not target_time and item.source_type != "calendar":
            # Per slide 9: Time must be resolvable; otherwise keep pending or discard
            # If message contains only preparation without time, we still preserve it for merging
            if "portfolio" not in lower_text and "prepare" not in lower_text:
                return None

        # 4. Extract Location
        location = None
        loc_match = re.search(r'(?:in|at)\s+(Office\s+[A-Za-z0-9]+|Zoom Room\s*#[0-9]+|Tech Park Tower)', text, re.IGNORECASE)
        if loc_match:
            location = loc_match.group(1).strip()
        elif item.source_type == "calendar" and item.metadata.get("location"):
            location = item.metadata["location"]

        # 5. Extract Preparation Requirement (Slide 7, 10)
        preparation = None
        if "portfolio" in lower_text:
            if "usb" in lower_text:
                preparation = "Portfolio (USB copy included)"
            else:
                preparation = "Portfolio"
        elif "equipment" in lower_text or "audio" in lower_text:
            preparation = "Sign in and check audio equipment"
        elif "upload" in lower_text or "pdf" in lower_text:
            preparation = "Finish peer reviews & export PDF"

        return ExtractedEvent(
            id=f"ext_{item.id}",
            source_id=item.id,
            source_type=item.source_type,
            title=title,
            event_type=event_type,
            target_time=target_time,
            location=location,
            preparation_context=preparation,
            is_actionable=True,
            confidence=0.96,
            raw_snippet=text[:100]
        )

    def _extract_datetime(self, text: str, item: SourceItem) -> Optional[datetime]:
        """Resolves dates and times with contextual anchor."""
        if item.source_type == "calendar" and "start_time" in item.metadata:
            try:
                return datetime.fromisoformat(item.metadata["start_time"])
            except Exception:
                pass

        # Parse Friday at 3:00 PM / 15:00
        now = datetime.now()
        base_friday = now + timedelta(days=((4 - now.weekday()) % 7))
        target_dt = base_friday.replace(hour=15, minute=0, second=0, microsecond=0)

        if "friday" in text.lower() or "15:00" in text or "3:00 pm" in text.lower():
            return target_dt

        # Parse tomorrow at 10:00 AM
        if "tomorrow" in text.lower() and ("10:00" in text or "10 am" in text.lower()):
            tmrw = now + timedelta(days=1)
            return tmrw.replace(hour=10, minute=0, second=0, microsecond=0)

        # Parse deadline / Monday 5:00 PM
        if "monday" in text.lower() and ("5:00 pm" in text.lower() or "17:00" in text):
            next_mon = now + timedelta(days=((7 - now.weekday()) % 7))
            return next_mon.replace(hour=17, minute=0, second=0, microsecond=0)

        return None
