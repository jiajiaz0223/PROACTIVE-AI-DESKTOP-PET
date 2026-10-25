import json,tempfile,unittest
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from proactive_pet.core import Store
from proactive_pet.ai.local_model import LocalModel
from proactive_pet.ai.time_validation import explicit_time
from test_core import FakeClock

class ActivityIntentTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[1]/'test-results'
        base.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base)
        self.store=Store(Path(self.temp.name)/'events.sqlite',FakeClock())
    def tearDown(self):
        self.store.close();self.temp.cleanup()
    def source(self,text='專題報告',manual=True):
        s=self.store.source(text,'test')
        s['user_requested_event']=manual
        return s
    def test_ignored_manual_activity_is_recoverable(self):
        source=self.source()
        self.store.ingest([{'action':'ignore','needs_review':False,'reason':'無時間'}],source)
        self.assertEqual(self.store.events(),[])
        self.assertEqual(len(self.store.pending()),1)
        self.assertEqual(self.store.pending()[0]['source']['content'],'專題報告')
        self.assertEqual(self.store.pending()[0]['proposal']['action'],'create')
        self.store.ingest([],source)
        self.assertEqual(len(self.store.pending()),1)
    def test_empty_manual_response_stays_pending(self):
        self.store.ingest([],self.source('跟朋友吃飯'))
        self.assertEqual(len(self.store.pending()),1)
        self.assertEqual(self.store.triggers(),[])
    def test_background_ads_stay_quiet(self):
        messages=self.store.ingest([{'action':'ignore','needs_review':True,'reason':'優惠宣傳'}],self.source('披薩五折',False))
        self.assertEqual(self.store.pending(),[])
        self.assertIn('優惠宣傳',messages[0])
    def test_mixed_result_does_not_create_spurious_review(self):
        p={'action':'create','title':'會議','time':'2026-10-12T13:00:00+08:00'}
        self.store.ingest([p,{'action':'ignore','reason':'廣告'}],self.source('下午一點會議，披薩五折'))
        self.assertEqual(len(self.store.events()),1)
        self.assertEqual(self.store.pending(),[])
    def test_missing_time_cannot_inherit_current_hour(self):
        client=LocalModel()
        proposal={'action':'create','title':'朋友聚餐','time':'2026-10-13T12:00:00+08:00',
                  'relative_minutes':None,'shift_minutes':None,'target_event_id':None,
                  'location':None,'preparations':[],'needs_review':False,'reason':'',
                  'evidence':'明天跟朋友吃飯'}
        with patch.object(client,'request',return_value={'message':{'content':json.dumps({'events':[proposal]})}}):
            source=self.source('明天跟朋友吃飯')
            results=client.analyze(source,[])
        self.store.ingest(results,source)
        self.assertEqual(self.store.events(),[])
        self.assertIn('日期與時間',self.store.pending()[0]['reason'])
    def test_uncertain_or_multiple_times_are_not_normalized(self):
        stamp=self.store.clock.now().isoformat()
        for text in ['明天可能下午三點吃飯','明天三點或四點開會','明天跟朋友吃飯','明天或後天下午三點吃飯']:
            self.assertIsNone(explicit_time(text,stamp),text)
    def test_explicit_time_keeps_day_and_hour(self):
        stamp=self.store.clock.now().isoformat()
        self.assertEqual(explicit_time('明天跟中午12:00朋友吃飯',stamp).isoformat(),'2026-10-13T12:00:00+08:00')
        self.assertEqual(explicit_time('十分鐘後打籃球',stamp).isoformat(),'2026-10-12T12:10:00+08:00')
    def test_ui_opens_pending_for_unrecognized_manual_activity(self):
        from proactive_pet.ui.app import Application
        root=tk.Tk();root.withdraw()
        callback_errors=[]
        root.report_callback_exception=lambda *args:callback_errors.append(args)
        project=Path(self.temp.name)
        app=Application(root,project,True,project/'ui-data')
        app.pet.window.withdraw()
        app.input.delete('1.0','end');app.input.insert('1.0','跟朋友吃飯')
        observed={}
        def finish():
            observed['pending']=app.store.pending()
            observed['tab']=app.notebook.select()==str(app.pending_tab)
            if observed['pending']:
                app.editor(pending=observed['pending'][0])
                windows=[w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and w is not app.pet.window]
                entries=[w for w in windows[-1].winfo_children() if w.winfo_class()=='TEntry']
                observed['blank_time']=entries[1].get()==''
            app.close()
        def ignored(client,*args):
            client.telemetry={'elapsed_ms':1,'model':'test-model'}
            return [{'action':'ignore','reason':'無時間'}]
        with patch.object(LocalModel,'analyze',autospec=True,side_effect=ignored),patch.object(LocalModel,'status',return_value=['qwen3:4b']):
            app.submit();root.after(1400,finish);root.mainloop()
        self.assertTrue(observed['tab'])
        self.assertTrue(observed['blank_time'])
        self.assertEqual(len(observed['pending']),1)
        self.assertEqual(callback_errors,[])

if __name__=='__main__':unittest.main()
