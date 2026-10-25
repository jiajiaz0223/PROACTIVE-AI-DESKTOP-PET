import tempfile,unittest,tkinter as tk
from pathlib import Path
from datetime import timedelta
from proactive_pet.ui.app import Application
from proactive_pet.core import parse_time,Store
from test_core import FakeClock

class ReminderDatesTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[1]/'test-results';base.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base)
        self.root=tk.Tk();self.root.withdraw()
        self.app=Application(self.root,Path(self.temp.name),True,Path(self.temp.name)/'data')
        self.app.pet.window.withdraw()
        self.clock=FakeClock();self.clock.demo=True
        self.app.clock=self.clock;self.app.store.clock=self.clock
    def tearDown(self):self.app.close();self.temp.cleanup()
    def add_tomorrow(self):
        when=(self.clock.now()+timedelta(days=1)).replace(hour=17,minute=37)
        self.app.store.manual('面試',when.isoformat(),preparations=['作品集'])
        self.app.refresh()
        return self.app.store.events()[0]
    def test_distinguishes_preparation_day_and_event_day(self):
        e=self.add_tomorrow();store=self.app.store
        triggers=store.triggers();prep=next(t for t in triggers if t['phase']=='preparation')
        action=next(t for t in triggers if t['phase']=='action')
        self.assertEqual(parse_time(prep['due']).strftime('%m/%d %H:%M'),'10/12 18:00')
        self.assertEqual(parse_time(action['due']).strftime('%m/%d %H:%M'),'10/13 17:36')
        self.assertEqual(self.app.tree.item(e['id'],'values')[-1],'準備 · 10/12 18:00')
        self.app.pet.show(prep,e)
        text=self.app.pet.text.cget('text')
        self.assertIn('準備提醒',text)
        self.assertIn('本次提醒：10/12 18:00',text)
        self.assertIn('活動時間：10/13 17:37',text)
        self.app.pet.render(action,e)
        self.assertIn('開始前提醒',self.app.pet.text.cget('text'))
    def test_disable_preparation_retains_only_next_day_action(self):
        e=self.add_tomorrow()
        prep=next(t for t in self.app.store.triggers() if t['phase']=='preparation')
        self.app.pet.show(prep,e)
        self.app.preparation_enabled.set(False);self.app.save_preferences()
        self.app.pump()
        self.assertIsNone(self.app.pet.current)
        self.assertEqual([t['phase'] for t in self.app.store.triggers()],['action'])
        self.assertEqual(self.app.tree.item(e['id'],'values')[-1],'開始前 · 10/13 17:36')
        with_other=Store(Path(self.temp.name)/'data/demo.sqlite',self.clock)
        try:self.assertFalse(with_other.settings['preparation_reminders'])
        finally:with_other.close()
    def test_reschedule_dismisses_old_visible_and_queued_notifications(self):
        store=self.app.store
        store.manual('會議',(self.clock.now()+timedelta(minutes=5)).isoformat())
        e=store.events()[0]
        self.clock.advance(240)
        old_trigger,old_event=store.tick()[0]
        self.app.pet.show(old_trigger,old_event)
        self.app.notifications.append((old_trigger,old_event))
        new_time=parse_time(e['time'])+timedelta(days=1)
        store.manual('會議',new_time.isoformat(),eid=e['id'])
        self.app.pump();self.app.refresh()
        self.assertIsNone(self.app.pet.current)
        self.assertEqual(self.app.notifications,[])
        self.assertEqual(self.app.pet.window.state(),'withdrawn')
        self.assertNotIn('10/12',self.app.tree.item(e['id'],'values')[-1])
        self.assertIn('10/13 12:04',self.app.tree.item(e['id'],'values')[-1])

if __name__=='__main__':unittest.main()
