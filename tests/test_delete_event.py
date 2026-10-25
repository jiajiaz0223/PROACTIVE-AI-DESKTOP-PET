import tempfile,unittest,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from datetime import timedelta
from proactive_pet.core import Store
from proactive_pet.ui.app import Application
from test_core import FakeClock

class DeleteEventTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[1]/'test-results';base.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base)
        self.clock=FakeClock();self.store=Store(Path(self.temp.name)/'events.sqlite',self.clock)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def add(self,name='待刪活動'):
        self.store.manual(name,(self.clock.now()+timedelta(minutes=5)).isoformat())
        return next(e for e in self.store.events() if e['title']==name)
    def test_delete_removes_all_reminders_and_survives_restart(self):
        event=self.add();other=self.add('保留活動')
        self.clock.advance(240)
        delivered=self.store.tick();trigger=next(t for t,e in delivered if e['id']==event['id'])
        self.store.snooze(trigger['id'],0.5)
        self.assertTrue(self.store.delete_event(event['id']))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM triggers WHERE event_id=?',(event['id'],)).fetchone()[0],0)
        path=self.store.path;self.store.close();self.store=Store(path,self.clock)
        self.assertIsNone(self.store.event(event['id']))
        self.assertIsNotNone(self.store.event(other['id']))
        self.clock.advance(30);self.assertEqual(self.store.tick(),[])
    def test_source_does_not_recreate_deleted_event(self):
        source=self.store.source('五分鐘後開會','local-file')
        p={'action':'create','title':'開會','relative_minutes':5}
        self.store.ingest([p],source)
        self.store.delete_event(self.store.events()[0]['id'])
        self.store.ingest([p],source)
        self.assertEqual(self.store.events(),[])
    def test_ui_confirmation_cancel_and_queued_reminder_cleanup(self):
        root=tk.Tk();root.withdraw()
        app=Application(root,Path(self.temp.name),True,Path(self.temp.name)/'ui')
        app.pet.window.withdraw()
        try:
            app.store.manual('測試事件',(app.clock.now()+timedelta(minutes=10)).isoformat())
            event=app.store.events()[0];app.refresh();app.tree.selection_set(event['id'])
            with patch('proactive_pet.ui.app.messagebox.askyesno',return_value=False):app.delete_selected()
            self.assertIsNotNone(app.store.event(event['id']))
            trigger=app.store.triggers()[0]
            app.pet.current=(trigger,event);app.notifications.append((trigger,event))
            with patch('proactive_pet.ui.app.messagebox.askyesno',return_value=True):app.delete_selected()
            self.assertIsNone(app.store.event(event['id']))
            self.assertEqual(app.notifications,[]);self.assertIsNone(app.pet.current)
            app.pump()
        finally:app.close()

if __name__=='__main__':unittest.main()
