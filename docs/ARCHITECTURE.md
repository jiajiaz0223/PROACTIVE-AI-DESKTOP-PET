# System Architecture: Proactive AI Desktop Pet

> Designed for **2026 ASUS UGen AI League — Lightweight Track (Battlefield Lightning)**  
> Hardware Target: **ASUS UGen300 AI Accelerator (Hailo-8 Edge NPU)**

---

## 1. High-Level Architecture Overview

Modern productivity tools suffer from a fragmentation gap: commitments and preparation details arrive across emails, chat applications, and calendar invites before ever being scheduled. **Proactive AI Desktop Pet** bridges this gap by acting as an autonomous, on-device companion that extracts commitments, plans intelligent lead-time reminders, and stays silent when not needed.

```
+---------------------------------------------------------------------------------------+
|                                ON-DEVICE PRIVACY BOUNDARY                             |
|                                                                                       |
|   +-----------------------+           +-------------------------------------------+   |
|   |  Authorized Sources   |           |         ASUS UGen300 Edge AI Pipeline     |   |
|   |  - Email (Local/IMAP) |  Trigger  |                                           |   |
|   |  - Messaging (Chat)   | --------> |  Local Reader --> INT8 Quantized Edge NPU |   |
|   |  - Calendar (ICS/Cal) |           |                   (Hailo-8 Slot-Filler)   |   |
|   +-----------------------+           +---------------------+---------------------+   |
|                                                             |                         |
|                                                             v                         |
|   +-------------------------------------------------------------------------------+   |
|   |                        Cross-Source Deduplication Engine                      |   |
|   |    Email (Time) + Chat (Preparation Requirement) + Calendar (Location)        |   |
|   |    ==> ONE Coherent Event Context (Unified Representation)                    |   |
|   +-------------------------------------------------------------------------------+   |
|                                             |                                         |
|                                             v                                         |
|   +-------------------------------------------------------------------------------+   |
|   |                     Dynamic Lead-Time Strategy Engine                         |   |
|   |  - Preparation lead times (e.g., Portfolio check the day before)              |   |
|   |  - Travel buffer lead times (e.g., 45 mins prior to departure)                |   |
|   |  - Quiet hours adjustment (22:00 - 08:00 muted/delayed)                       |   |
|   |  - Anti-fatigue capping & minimum trigger spacing                             |   |
|   +-------------------------------------------------------------------------------+   |
|                                             |                                         |
|                                             v                                         |
|   +-------------------------------------------------------------------------------+   |
|   |                    Update-Triggered Scheduler & Pet UI                        |   |
|   |  - Idle CPU < 0.5% (Zero continuous background inference loops)               |   |
|   |  - Desktop Pet Widget: "What's next, time remaining, what to do now"         |   |
|   |  - User Feedback Controls: [View details] [Remind me later] [Prep done]       |   |
|   +-------------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Pillars

### Pillar 1: Update-Triggered Analysis (Slide 15)
Traditional AI assistants poll large language models continuously in the background, consuming substantial CPU, battery, and memory. Our architecture adopts an **event-driven, update-triggered approach**:
- **Zero background inference while idle**: The AI model only runs when a new email, chat message, or calendar entry arrives.
- **Scheduler-driven dispatch**: Once reminder strategies are formulated and registered, ordinary OS timers execute the notifications.
- **Device resource footprint**:
  - Idle CPU consumption: `< 0.5%`
  - Active memory footprint: `< 50 MB`
  - Analysis latency on ASUS UGen300: `< 30 ms`

### Pillar 2: Cross-Source Multi-Modal Deduplication (Slide 8)
When users coordinate events, details are often fragmented:
- **Email**: Contains event type and primary timestamp (*"Interview on Friday at 15:00"*).
- **Slack/Teams Chat**: Contains urgent instructions (*"Please bring your portfolio"*).
- **Calendar**: Contains venue information (*"Interview in Office A"*).

The **Deduplication Engine** matches temporal proximity and semantic similarity to merge these inputs into a single composite `MergedEvent`, preventing annoying duplicate alarms.

### Pillar 3: Adaptive Preparation & Travel Lead Times (Slide 10)
Rather than rigid fixed intervals (e.g., 10 minutes prior for everything), the strategy engine customizes prompts based on preparation cost:
1. **Interview**: Requires portfolio preparation the evening before + departure buffer before transit.
2. **Online Meeting**: Requires equipment and audio check 10 minutes before start.
3. **Document Submission**: Requires draft review the day before + upload verification 1 hour prior to deadline.

---

## 3. Dynamic State & Replanning (Slide 11)

The system respects user feedback and changes in real time:
- **Preparation Done**: Clicking "Preparation Done" immediately drops further preparation reminders while preserving departure alerts.
- **Rescheduled**: When meeting times shift, pending schedules are evicted and recalculated cleanly.
- **Canceled / Completed**: When an event is finished or dismissed, all downstream notifications are halted.
