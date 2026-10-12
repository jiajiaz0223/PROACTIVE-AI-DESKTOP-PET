"""Cross-source event deduplication and unification engine.

Merges complementary information from email, chat messages, and calendar
into a single consolidated event context (Slide 8).
"""

from datetime import datetime, timedelta
from typing import List, Dict
from proactive_pet.models import ExtractedEvent, MergedEvent


class EventDeduplicator:
    """Combines fragmented inputs across multiple channels into single coherent events."""

    def merge_events(self, extracted_events: List[ExtractedEvent]) -> List[MergedEvent]:
        """Merges matching events based on event type, target time proximity, and title."""
        merged_groups: Dict[str, MergedEvent] = {}

        for item in extracted_events:
            if not item.is_actionable:
                continue

            matched_key = self._find_matching_group(item, merged_groups)

            if matched_key:
                group = merged_groups[matched_key]
                # Supplement missing fields
                if not group.location and item.location:
                    group.location = item.location
                if item.preparation_context and item.preparation_context not in group.preparations:
                    group.preparations.append(item.preparation_context)
                if item.source_id not in group.source_ids:
                    group.source_ids.append(item.source_id)
                    group.source_descriptions.append(f"{item.source_type} ({item.source_id})")
            else:
                # If target_time is None (e.g. an isolated message prompt), try to link with an existing event
                if not item.target_time:
                    for g in merged_groups.values():
                        if item.preparation_context and item.preparation_context not in g.preparations:
                            g.preparations.append(item.preparation_context)
                            g.source_ids.append(item.source_id)
                            g.source_descriptions.append(f"{item.source_type} ({item.source_id})")
                            break
                    continue

                # Create new merged event
                key = f"{item.event_type}_{item.target_time.strftime('%Y%m%d_%H%M')}"
                preps = [item.preparation_context] if item.preparation_context else []
                merged_groups[key] = MergedEvent(
                    id=f"merged_{key}",
                    title=item.title,
                    event_type=item.event_type,
                    target_time=item.target_time,
                    location=item.location,
                    preparations=preps,
                    source_ids=[item.source_id],
                    source_descriptions=[f"{item.source_type} ({item.source_id})"]
                )

        return list(merged_groups.values())

    def _find_matching_group(self, item: ExtractedEvent, current_groups: Dict[str, MergedEvent]) -> str:
        """Finds if a group already exists that refers to the same event."""
        if not item.target_time:
            return ""

        for key, group in current_groups.items():
            # Check event type matching
            if group.event_type == item.event_type:
                # Within 2 hours tolerance
                time_diff = abs((group.target_time - item.target_time).total_seconds())
                if time_diff <= 7200:
                    return key

        return ""
