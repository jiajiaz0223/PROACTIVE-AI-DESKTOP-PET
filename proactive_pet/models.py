"""Core data models representing sources, events, strategies, and reminders."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class SourceItem:
    """Represents an item ingested from an authorized personal source."""
    id: str
    source_type: str  # 'email', 'message', 'calendar'
    sender_or_owner: str
    content: str
    timestamp: datetime
    is_authorized: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedEvent:
    """Structured event extracted by on-device Edge AI from natural language."""
    id: str
    source_id: str
    source_type: str
    title: str
    event_type: str  # 'interview', 'meeting', 'submission', 'general'
    target_time: Optional[datetime] = None
    location: Optional[str] = None
    preparation_context: Optional[str] = None
    is_actionable: bool = True
    confidence: float = 0.95
    raw_snippet: str = ""


@dataclass
class MergedEvent:
    """Unified single context resulting from deduplication across sources."""
    id: str
    title: str
    event_type: str
    target_time: datetime
    location: Optional[str] = None
    preparations: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    source_descriptions: List[str] = field(default_factory=list)
    is_preparation_done: bool = False
    is_cancelled: bool = False
    is_completed: bool = False


@dataclass
class ScheduledTrigger:
    """A planned prompt moment with its purpose and message."""
    trigger_id: str
    event_id: str
    trigger_time: datetime
    phase: str  # 'preparation', 'action', 'final_notice'
    prompt_message: str
    lead_time_desc: str
    triggered: bool = False
    snoozed_until: Optional[datetime] = None


@dataclass
class ReminderStrategy:
    """Proactive reminder strategy calculated for an event."""
    event_id: str
    triggers: List[ScheduledTrigger] = field(default_factory=list)
    rationale: str = ""
    max_count: int = 3
    min_spacing_minutes: int = 30
