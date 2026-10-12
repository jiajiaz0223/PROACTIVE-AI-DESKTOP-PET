"""Proactive reminder strategy calculation engine (Slide 10 & 11).

Calculates intelligent lead times based on preparation needs, travel buffers,
and user quiet hours. Handles dynamic state updates (rescheduled, cancelled,
preparation done).
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from proactive_pet.models import MergedEvent, ReminderStrategy, ScheduledTrigger


class ReminderStrategyEngine:
    """Derives context-aware reminder schedules rather than fixed intervals."""

    def __init__(self, quiet_hours_start: int = 22, quiet_hours_end: int = 8):
        self.quiet_hours_start = quiet_hours_start  # 22:00
        self.quiet_hours_end = quiet_hours_end      # 08:00
        self.max_reminder_count = 3
        self.min_spacing_minutes = 30

    def generate_strategy(self, event: MergedEvent) -> ReminderStrategy:
        """Generates a bounded reminder strategy for a merged event."""
        if event.is_cancelled or event.is_completed:
            return ReminderStrategy(
                event_id=event.id,
                triggers=[],
                rationale="Event is cancelled or already completed. Reminders stopped."
            )

        triggers: List[ScheduledTrigger] = []
        prep_text = ", ".join(event.preparations) if event.preparations else "standard preparation"

        # 1. Interview Strategy
        if event.event_type == "interview":
            rationale = "Interview requires portfolio preparation the day before & 45m travel buffer before departure."
            
            # Preparation trigger: Day before (if not already done)
            if not event.is_preparation_done:
                day_before = event.target_time - timedelta(days=1)
                day_before_trigger = day_before.replace(hour=18, minute=0, second=0)
                triggers.append(
                    ScheduledTrigger(
                        trigger_id=f"{event.id}_prep",
                        event_id=event.id,
                        trigger_time=self._adjust_for_quiet_hours(day_before_trigger),
                        phase="preparation",
                        prompt_message=f"Upcoming Interview tomorrow at {event.target_time.strftime('%H:%M')}! Remember to prepare: {prep_text}.",
                        lead_time_desc="The day before (Preparation)"
                    )
                )

            # Departure / Action trigger: 45 minutes before
            action_time = event.target_time - timedelta(minutes=45)
            triggers.append(
                ScheduledTrigger(
                    trigger_id=f"{event.id}_action",
                    event_id=event.id,
                    trigger_time=self._adjust_for_quiet_hours(action_time),
                    phase="action",
                    prompt_message=f"Your interview starts in 45 minutes at {event.location or 'designated venue'}. Time to depart! Ensure {prep_text} is packed.",
                    lead_time_desc="45 mins before (Departure)"
                )
            )

        # 2. Online Meeting Strategy
        elif event.event_type == "meeting":
            rationale = "Online sync requires audio/video equipment check 10 minutes prior."
            action_time = event.target_time - timedelta(minutes=10)
            triggers.append(
                ScheduledTrigger(
                    trigger_id=f"{event.id}_meeting_prep",
                    event_id=event.id,
                    trigger_time=self._adjust_for_quiet_hours(action_time),
                    phase="action",
                    prompt_message=f"Online meeting starts in 10 minutes ({event.title}). Please sign in and check audio equipment.",
                    lead_time_desc="10 mins before (Equipment check)"
                )
            )

        # 3. Document Submission Strategy
        elif event.event_type == "submission":
            rationale = "Submission requires draft completion the day before and final upload 1 hour before deadline."
            if not event.is_preparation_done:
                day_before = event.target_time - timedelta(days=1)
                day_before_trigger = day_before.replace(hour=16, minute=0, second=0)
                triggers.append(
                    ScheduledTrigger(
                        trigger_id=f"{event.id}_sub_draft",
                        event_id=event.id,
                        trigger_time=self._adjust_for_quiet_hours(day_before_trigger),
                        phase="preparation",
                        prompt_message=f"Deadline tomorrow for {event.title}! Please finish {prep_text}.",
                        lead_time_desc="The day before (Draft & Review)"
                    )
                )
            action_time = event.target_time - timedelta(hours=1)
            triggers.append(
                ScheduledTrigger(
                    trigger_id=f"{event.id}_sub_final",
                    event_id=event.id,
                    trigger_time=self._adjust_for_quiet_hours(action_time),
                    phase="action",
                    prompt_message=f"1 hour left until {event.title} deadline! Please upload the final PDF file.",
                    lead_time_desc="1 hour before (Final upload)"
                )
            )

        # Default fallback
        else:
            rationale = "Standard commitment lead time."
            action_time = event.target_time - timedelta(minutes=15)
            triggers.append(
                ScheduledTrigger(
                    trigger_id=f"{event.id}_general",
                    event_id=event.id,
                    trigger_time=self._adjust_for_quiet_hours(action_time),
                    phase="action",
                    prompt_message=f"Upcoming commitment: {event.title} at {event.target_time.strftime('%H:%M')}.",
                    lead_time_desc="15 mins before"
                )
            )

        # Enforce max count cap and sort by trigger time
        triggers.sort(key=lambda x: x.trigger_time)
        bounded_triggers = triggers[:self.max_reminder_count]

        return ReminderStrategy(
            event_id=event.id,
            triggers=bounded_triggers,
            rationale=rationale,
            max_count=self.max_reminder_count,
            min_spacing_minutes=self.min_spacing_minutes
        )

    def _adjust_for_quiet_hours(self, dt: datetime) -> datetime:
        """Pushes reminders out of quiet hours (22:00 - 08:00) into active time."""
        hour = dt.hour
        if self.quiet_hours_start <= hour or hour < self.quiet_hours_end:
            # Shift to 08:05 next morning
            if hour >= self.quiet_hours_start:
                next_day = dt + timedelta(days=1)
                return next_day.replace(hour=self.quiet_hours_end, minute=5, second=0)
            else:
                return dt.replace(hour=self.quiet_hours_end, minute=5, second=0)
        return dt
