import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from proactive_pet.core import Store, TZ, Clock, parse_time
from proactive_pet.ai.local_model import LocalModel
from proactive_pet.ingestion.files import calendar_items, calendar_proposals, read_source


class FakeClock:
    def __init__(self): self.value=datetime(2026,10,12,12,0,tzinfo=TZ)
    def now(self): return self.value
    def advance(self,seconds): self.value+=timedelta(seconds=seconds)


class CoreTests(unittest.TestCase):
    def setUp(self):
        test_root=Path(__file__).resolve().parents[1]/'test-results'
        test_root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=test_root)
        self.clock=FakeClock()
        self.store=Store(Path(self.temp.name)/'test.sqlite',self.clock)

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def create(self,title='Project meeting',minutes=5,preps=None):
        self.store.manual(title,(self.clock.now()+timedelta(minutes=minutes)).isoformat(),preparations=preps)
        return next(e for e in self.store.events() if e['title']==title)

    def test_real_reminder_once(self):
        self.create();self.assertEqual(self.store.tick(),[])
        self.clock.advance(240)
        self.assertEqual(len(self.store.tick()),1)
        self.assertEqual(self.store.tick(),[])

    def test_restart_restores_and_does_not_redeliver(self):
        self.create();path=self.store.path;self.store.close()
        self.store=Store(path,self.clock);self.clock.advance(240)
        self.assertEqual(len(self.store.tick()),1)
        self.store.close();self.store=Store(path,self.clock)
        self.assertEqual(self.store.tick(),[])

    def test_reschedule_keeps_id_and_removes_old_trigger(self):
        e=self.create();self.clock.advance(60)
        source=self.store.source('Delay this by ten minutes','user')
        self.store.ingest([{'action':'update','target_event_id':e['id'],'shift_minutes':10}],source)
        self.assertEqual(len(self.store.events()),1)
        self.clock.advance(180);self.assertEqual(self.store.tick(),[])
        self.clock.advance(600);self.assertEqual(len(self.store.tick()),1)

    def test_cancel_stops_reminders(self):
        e=self.create()
        self.store.ingest([{'action':'cancel','target_event_id':e['id']}],self.store.source('cancel','user'))
        self.clock.advance(240);self.assertEqual(self.store.tick(),[])
        self.assertEqual(self.store.event(e['id'])['status'],'cancelled')

    def test_preparation_done_persists(self):
        e=self.create(minutes=48*60,preps=['Slides'])
        self.assertEqual(len(self.store.triggers()),2)
        self.store.mark(e['id'],'prep_done');self.store.replan_all()
        self.assertEqual([t['phase'] for t in self.store.triggers()],['action'])

    def test_similar_interviews_stay_distinct(self):
        self.create('Company A interview',60)
        self.create('Company B interview',120)
        self.assertEqual(len(self.store.events()),2)

    def test_same_title_different_venue_stays_distinct(self):
        when=(self.clock.now()+timedelta(hours=2)).isoformat()
        self.store.manual('Interview',when,'Office A');self.store.manual('Interview',when,'Office B')
        self.assertEqual(len(self.store.events()),2)

    def test_exact_duplicate_merges_sources(self):
        e=self.create()
        p={'action':'create','title':e['title'],'time':e['time'],'preparations':['Slides']}
        s=self.store.source('same event extra details','email')
        self.store.ingest([p],s);self.store.ingest([p],s)
        self.assertEqual(len(self.store.events()),1)
        self.assertEqual(len(self.store.event(e['id'])['sources']),2)

    def test_ambiguous_update_pending(self):
        self.create()
        self.store.ingest([{'action':'update','shift_minutes':10}],self.store.source('delay meeting','email'))
        self.assertEqual(len(self.store.pending()),1)

    def test_missing_time_pending(self):
        self.store.ingest([{'action':'create','title':'Interview'}],self.store.source('Interview soon','email'))
        self.assertEqual(len(self.store.pending()),1);self.assertEqual(self.store.events(),[])

    def test_past_not_moved_to_future(self):
        self.store.ingest([{'action':'create','title':'Old','time':'2026-10-10T15:00:00+08:00'}],self.store.source('old','email'))
        self.assertEqual(self.store.events(),[]);self.assertEqual(len(self.store.pending()),1)

    def test_relative_time_uses_source_timestamp(self):
        source=self.store.source('five minutes later','email',self.clock.now()+timedelta(days=1))
        self.store.ingest([{'action':'create','title':'Tomorrow','relative_minutes':5}],source)
        self.assertEqual(parse_time(self.store.events()[0]['time']),self.clock.now()+timedelta(days=1,minutes=5))

    def test_quiet_hours_never_push_after_event(self):
        self.store.set_setting('quiet',True)
        self.store.manual('Early meeting','2026-10-13T07:30:00+08:00')
        t=self.store.triggers()[0]
        self.assertEqual(parse_time(t['due']),datetime(2026,10,12,21,59,tzinfo=TZ))

    def test_expired_triggers_skip_on_restart(self):
        self.create();self.clock.advance(3600)
        self.assertEqual(self.store.tick(),[]);self.assertEqual(self.store.triggers(),[])

    def test_snooze_delivery_cap(self):
        e=self.create(minutes=120);self.store.set_setting('lead_minutes',100);self.store.replan_all()
        self.clock.advance(1200);t,_=self.store.tick()[0]
        for _ in range(2):
            self.store.snooze(t['id'],1);self.clock.advance(60);t,_=self.store.tick()[0]
        with self.assertRaises(ValueError):self.store.snooze(t['id'],1)

    def test_snooze_does_not_exceed_event(self):
        self.create();self.clock.advance(240);t,_=self.store.tick()[0]
        with self.assertRaises(ValueError):self.store.snooze(t['id'],15)

    def test_multiple_events(self):
        source=self.store.source('two events','email')
        self.store.ingest([{'action':'create','title':'A','relative_minutes':10},
                           {'action':'create','title':'B','relative_minutes':20}],source)
        self.assertEqual(len(self.store.events()),2)

    def test_cloud_endpoint_rejected(self):
        with self.assertRaises(ValueError):LocalModel(base_url='https://example.com')

    def test_calendar_utc(self):
        events=calendar_items('BEGIN:VEVENT\nUID:test\nDTSTART:20261016T070000Z\nSUMMARY:Interview\nEND:VEVENT')
        self.assertEqual(parse_time(events[0]['time']).hour,15)

    def test_calendar_recurrence_rejected(self):
        with self.assertRaises(ValueError):calendar_items('BEGIN:VEVENT\nDTSTART:20261016T070000Z\nRRULE:FREQ=DAILY\nEND:VEVENT')

    def test_calendar_uid_update(self):
        text='BEGIN:VEVENT\nUID:test\nDTSTART:20261016T070000Z\nSUMMARY:Interview\nEND:VEVENT'
        p=calendar_proposals(text,[])[0];source=self.store.source(text,'cal');source['calendar_uid']=p['calendar_uid']
        self.store.ingest([p],source)
        text=text.replace('070000','080000')
        p=calendar_proposals(text,self.store.events())[0]
        self.assertEqual(p['action'],'update')
        self.store.ingest([p],self.store.source(text,'cal'))
        self.assertEqual(len(self.store.events()),1)
        self.assertEqual(parse_time(self.store.events()[0]['time']).hour,16)

    def test_real_clock_cannot_advance(self):
        with self.assertRaises(ValueError):Clock().advance(60)


if __name__=='__main__':unittest.main(verbosity=2)
