"""Interactive floating Desktop Pet widget with speech bubble and action controls.

Implements the user interaction model defined in Slide 13:
- "What is next, how long remains, and what to do now."
- Controls: [View details], [Remind me later], [Preparation done]
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from proactive_pet.models import ScheduledTrigger, MergedEvent


class DesktopPetWindow:
    """Floating on-screen AI pet with animated expression and proactive speech bubble."""

    def __init__(self, root: tk.Tk, on_action_callback: Optional[Callable[[str, str], None]] = None):
        self.root = root
        self.on_action = on_action_callback
        self.current_trigger: Optional[ScheduledTrigger] = None
        self.current_event: Optional[MergedEvent] = None

        # Setup pet window
        self.root.title("Proactive AI Desktop Pet")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)  # Frameless floating pet
        self.root.geometry("340x260+1100+550")
        self.root.configure(bg="#1E222D")

        # Dragging support
        self._drag_start_x = 0
        self._drag_start_y = 0
        self.root.bind("<ButtonPress-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._on_drag)

        self._build_ui()
        self._blink_counter = 0
        self._animate_pet()

    def _build_ui(self):
        """Constructs pet visual avatar and notification card."""
        self.main_frame = tk.Frame(self.root, bg="#1E222D", highlightbackground="#3B82F6", highlightthickness=2)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Header / Status bar
        self.top_bar = tk.Frame(self.main_frame, bg="#181B24", height=24)
        self.top_bar.pack(fill=tk.X, side=tk.TOP)

        self.title_label = tk.Label(
            self.top_bar,
            text="🐾 ASUS UGen AI Pet (Offline)",
            font=("Segoe UI", 9, "bold"),
            fg="#60A5FA",
            bg="#181B24"
        )
        self.title_label.pack(side=tk.LEFT, padx=6)

        self.close_btn = tk.Label(
            self.top_bar,
            text="✕",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#181B24",
            cursor="hand2"
        )
        self.close_btn.pack(side=tk.RIGHT, padx=6)
        self.close_btn.bind("<Button-1>", lambda e: self.minimize_or_hide())

        # Pet Avatar representation
        self.pet_canvas = tk.Canvas(self.main_frame, width=320, height=80, bg="#1E222D", highlightthickness=0)
        self.pet_canvas.pack(pady=4)

        # Speech bubble / Proactive reminder box
        self.bubble_frame = tk.Frame(self.main_frame, bg="#282F3F", bd=1, relief=tk.SOLID)
        self.bubble_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.bubble_text = tk.Label(
            self.bubble_frame,
            text="“Hello! I am your local AI companion. I quietly monitor your plans and will proactively remind you when needed.”",
            font=("Segoe UI", 9),
            fg="#F8FAFC",
            bg="#282F3F",
            wraplength=300,
            justify=tk.LEFT
        )
        self.bubble_text.pack(padx=8, pady=6, anchor="w")

        # Context Tag
        self.context_tag = tk.Label(
            self.bubble_frame,
            text="Status: Guarding your schedule locally",
            font=("Segoe UI", 8, "italic"),
            fg="#94A3B8",
            bg="#282F3F"
        )
        self.context_tag.pack(padx=8, pady=1, anchor="w")

        # Action Buttons (Slide 13)
        self.button_frame = tk.Frame(self.bubble_frame, bg="#282F3F")
        self.button_frame.pack(fill=tk.X, padx=6, pady=6)

        self.btn_details = tk.Button(
            self.button_frame,
            text="View details",
            font=("Segoe UI", 8),
            bg="#3B82F6",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_view_details
        )
        self.btn_details.pack(side=tk.LEFT, padx=3)

        self.btn_snooze = tk.Button(
            self.button_frame,
            text="Remind me later",
            font=("Segoe UI", 8),
            bg="#475569",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_snooze
        )
        self.btn_snooze.pack(side=tk.LEFT, padx=3)

        self.btn_prep = tk.Button(
            self.button_frame,
            text="Preparation done",
            font=("Segoe UI", 8),
            bg="#10B981",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_prep_done
        )
        self.btn_prep.pack(side=tk.RIGHT, padx=3)

    def draw_pet(self, eyes_open: bool = True):
        """Draws the cute robotic AI pet avatar inspired by Slide 1."""
        self.pet_canvas.delete("all")
        # Ears
        self.pet_canvas.create_polygon(120, 15, 140, 35, 120, 45, fill="#38BDF8", outline="#0284C7")
        self.pet_canvas.create_polygon(200, 15, 180, 35, 200, 45, fill="#38BDF8", outline="#0284C7")
        # Head
        self.pet_canvas.create_oval(115, 20, 205, 75, fill="#E2E8F0", outline="#94A3B8", width=2)
        # Face screen
        self.pet_canvas.create_oval(128, 28, 192, 68, fill="#0F172A", outline="#38BDF8", width=2)

        # Eyes
        if eyes_open:
            self.pet_canvas.create_oval(140, 40, 152, 56, fill="#06B6D4", outline="#22D3EE")
            self.pet_canvas.create_oval(144, 43, 148, 48, fill="#FFFFFF")
            self.pet_canvas.create_oval(168, 40, 180, 56, fill="#06B6D4", outline="#22D3EE")
            self.pet_canvas.create_oval(172, 43, 176, 48, fill="#FFFFFF")
        else:
            # Blinking arc
            self.pet_canvas.create_line(140, 48, 152, 48, fill="#22D3EE", width=3)
            self.pet_canvas.create_line(168, 48, 180, 48, fill="#22D3EE", width=3)

        # Cute mouth / badge
        self.pet_canvas.create_oval(158, 60, 162, 64, fill="#38BDF8")

    def _animate_pet(self):
        """Simple animation loop for blinking and alive feeling."""
        self._blink_counter += 1
        if self._blink_counter % 25 == 0:
            self.draw_pet(eyes_open=False)
        else:
            self.draw_pet(eyes_open=True)
        self.root.after(120, self._animate_pet)

    def display_trigger(self, trigger: ScheduledTrigger, event: Optional[MergedEvent] = None):
        """Presents a proactive prompt from the scheduler."""
        self.current_trigger = trigger
        self.current_event = event
        self.bubble_text.config(text=f"“{trigger.prompt_message}”")
        src_info = ", ".join(event.source_descriptions) if event else "Authorized Sources"
        self.context_tag.config(text=f"Source: {src_info} • Phase: {trigger.lead_time_desc}")
        # Pulse visual highlight
        self.main_frame.config(highlightbackground="#F59E0B")

    def minimize_or_hide(self):
        """Hides speech bubble or parks pet."""
        self.bubble_text.config(text="“I'm watching over your schedule quietly in the background.”")
        self.context_tag.config(text="Status: Idling (Low Energy Mode)")
        self.main_frame.config(highlightbackground="#3B82F6")

    def _on_view_details(self):
        if self.current_event:
            details = (
                f"Event: {self.current_event.title}\n"
                f"Time: {self.current_event.target_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"Location: {self.current_event.location or 'N/A'}\n"
                f"Preparations: {', '.join(self.current_event.preparations) if self.current_event.preparations else 'None'}\n"
                f"Sources merged: {', '.join(self.current_event.source_descriptions)}"
            )
            messagebox.showinfo("Event Details", details)
        else:
            messagebox.showinfo("Desktop Pet", "No active event details available right now.")

    def _on_snooze(self):
        if self.current_trigger and self.on_action:
            self.on_action("snooze", self.current_trigger.trigger_id)
            self.bubble_text.config(text="“Okay! I'll remind you again in 15 minutes.”")
            self.context_tag.config(text="Action: Snoozed")

    def _on_prep_done(self):
        if self.current_trigger and self.on_action:
            self.on_action("prep_done", self.current_trigger.event_id)
            self.bubble_text.config(text="“Great job! I have updated your schedule and cancelled preparation prompts.”")
            self.context_tag.config(text="Action: Preparation Marked Done")

    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_start_x)
        y = self.root.winfo_y() + (event.y - self._drag_start_y)
        self.root.geometry(f"+{x}+{y}")
