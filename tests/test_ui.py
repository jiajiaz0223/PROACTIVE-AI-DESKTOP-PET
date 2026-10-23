"""Real Tk event-loop smoke test using a manually created event (no fake AI)."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from datetime import timedelta
import tkinter as tk
from proactive_pet.ui.app import Application


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Display required')
class UIIntegrationTest(unittest.TestCase):
    def test_timer_delivers_without_trigger_button(self):
        base=Path(__file__).resolve().parents[1]/'test-results'
        base.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            project=Path(tmp)
            root=tk.Tk()
            app=Application(root,project,data_dir=project/'data')
            root.withdraw();app.pet.window.withdraw()
            try:
                app.store.manual('Automatic timer integration',
                    (app.clock.now()+timedelta(seconds=62)).isoformat())
                deadline=time.monotonic()+5
                while time.monotonic()<deadline and app.pet.current is None:
                    root.update();time.sleep(0.02)
                self.assertIsNotNone(app.pet.current,'Tk event loop did not deliver the due reminder')
                self.assertEqual(app.pet.current[1]['title'],'Automatic timer integration')
            finally:
                app.close()
