"""Main application entry point for Proactive AI Desktop Pet.

Launches both the floating on-screen AI pet widget and the ASUS UGen300
hackathon evaluation dashboard.
"""

import os
import sys
import tkinter as tk
from datetime import datetime

# Add root directory to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from proactive_pet.ingestion.reader import LocalSourceReader
from proactive_pet.ai.extractor import LocalAIExtractor
from proactive_pet.ai.hailo_ugen300_adapter import ASUSUGen300Adapter
from proactive_pet.engine.deduplicator import EventDeduplicator
from proactive_pet.engine.strategy_engine import ReminderStrategyEngine
from proactive_pet.engine.scheduler import UpdateTriggeredScheduler
from proactive_pet.ui.pet_window import DesktopPetWindow
from proactive_pet.ui.control_panel import HackathonControlPanel


def main():
    fixtures_dir = os.path.join(current_dir, "fixtures")

    # 1. Initialize core pipeline modules
    reader = LocalSourceReader(fixtures_dir=fixtures_dir)
    hw_adapter = ASUSUGen300Adapter(use_simulation=True)
    extractor = LocalAIExtractor(hardware_adapter=hw_adapter)
    deduplicator = EventDeduplicator()
    strategy_engine = ReminderStrategyEngine()
    scheduler = UpdateTriggeredScheduler()

    # 2. Setup Tkinter UI Roots
    # Primary window: Evaluation Dashboard
    dashboard_root = tk.Tk()

    # Secondary window: Floating Desktop Pet
    pet_toplevel = tk.Toplevel(dashboard_root)

    def on_pet_action(action_type: str, item_id: str):
        if action_type == "snooze":
            scheduler.snooze_trigger(item_id, minutes=15)
        elif action_type == "prep_done":
            scheduler.mark_preparation_done(item_id)

    pet_window = DesktopPetWindow(pet_toplevel, on_action_callback=on_pet_action)

    panel = HackathonControlPanel(
        root=dashboard_root,
        reader=reader,
        extractor=extractor,
        deduplicator=deduplicator,
        strategy_engine=strategy_engine,
        scheduler=scheduler,
        pet_window=pet_window
    )

    print("================================================================")
    print(" ASUS UGen AI League 2026 - Lightweight Track")
    print(" PROACTIVE AI DESKTOP PET Running Successfully!")
    print(" - Evaluation Dashboard: Interactive control and hardware monitor")
    print(" - Desktop Pet Widget: Floating at bottom-right of your screen")
    print("================================================================")

    dashboard_root.mainloop()


if __name__ == "__main__":
    main()
