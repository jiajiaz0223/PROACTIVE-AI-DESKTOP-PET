# Demo Guide & 3-Minute Video Walkthrough Script

> ASUS Hackathon Stage I Requirement: **Under 3-minute practical demo video**  
> Demo Sequence Protocol: **Slide 17 of Stage I Proposal**

---

## 1. Quick Launch Options

### Option A: Interactive GUI Demo (Floating Pet + Judge Dashboard)
Run the following command in terminal:
```bash
python run_pet.py
```
- A floating cyber pet widget appears at the lower right of your screen.
- The evaluation dashboard opens, allowing step-by-step trigger execution.

### Option B: Automated Headless Benchmark (Zero display required)
```bash
python run_offline_benchmark.py
```
- Validates the entire pipeline from ingestion to deduplication, strategy generation, dynamic replanning, and resource telemetry in seconds.

---

## 2. 6-Step Live Demo Protocol (Slide 17)

Follow these exact 6 steps on the evaluation dashboard or during video recording:

| Step | Action on UI | Expected Outcome & Narration Point |
| :---: | :--- | :--- |
| **1** | Click **"1. Prepare Local Data"** | Loads 8 items from `fixtures/` representing email invitations, Slack messages, and calendar entries. Emphasize that all data is local. |
| **2** | Click **"2. Disable Networking"** | Verifies offline continuity. Show that zero network traffic leaves the machine. |
| **3** | Click **"3. Read & Analyze on Edge NPU"** | Simulates ASUS UGen300 (Hailo-8) INT8 execution. Show average extraction latency (~28.4 ms) and discard of irrelevant items. |
| **4** | Click **"4. Show Merged Strategy & Source Context"** | **Demonstrates Slide 8**: Email + Message + Calendar merged into **ONE EVENT**: *Job Interview • Friday 15:00 • Office A • Portfolio*. Rationale and lead times are clearly calculated. |
| **5** | Click **"5. Trigger Live Pet Proactive Reminder"** | The desktop pet pops up a speech bubble with the actionable prompt: *“Your interview starts in 45 minutes... Ensure Portfolio is packed.”* |
| **6** | Click **"Preparation done"** on Pet | **Demonstrates Slide 11**: Preparation prompt is cleared, but departure alert remains scheduled. Shows that the AI pet adapts dynamically. |

---

## 3. 3-Minute Video Recording Script

- **0:00 - 0:30 (Problem)**: Show fragmented apps (Email, Slack, Calendar). Explain that crucial preparation details get lost before reaching the calendar.
- **0:30 - 1:15 (On-Device Solution & Hardware)**: Introduce Proactive AI Desktop Pet powered by ASUS UGen300 (Hailo-8). Highlight 100% offline data privacy and ~28ms NPU inference speed.
- **1:15 - 2:00 (Cross-Source Deduplication & Pet Interaction)**: Show how 3 fragmented items become 1 clear event. Demonstrate the floating pet delivering timely, actionable prompts.
- **2:00 - 2:40 (Adaptive Dynamics & Resource Efficiency)**: Click "Preparation done", show automatic schedule adaptation, and display `< 0.5%` idle CPU usage.
- **2:40 - 3:00 (Summary & Commercial Impact)**: Conclude with target market (freelancers & students) and ASUS hardware synergy.
