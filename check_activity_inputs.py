from pathlib import Path
from datetime import datetime
import json,sys,tempfile
from proactive_pet.ai.local_model import LocalModel
from proactive_pet.core import Store,TZ,parse_time

class FixedClock:
    def now(self):return datetime(2026,10,25,15,0,tzinfo=TZ)

cases=[
('meal_no_time','跟朋友吃飯','pending'),
('interview_no_time','設計師面試','pending'),
('report_no_time','專題報告','pending'),
('meeting_no_time','小組會議','pending'),
('tomorrow_without_hour','明天跟朋友吃飯','pending'),
('meal_explicit','明天下午一點跟朋友吃飯','event'),
('user_original_word_order','明天跟中午12:00朋友吃飯','event'),
('remind_request','提醒我明天下午三點去看牙醫','event'),
('activity_not_work','十分鐘後打籃球','event'),
('advert_background','本週披薩全面五折！點我領取優惠。','ignore'),
]
expected_times={'meal_explicit':datetime(2026,10,26,13,0,tzinfo=TZ),
                'user_original_word_order':datetime(2026,10,26,12,0,tzinfo=TZ),
                'remind_request':datetime(2026,10,26,15,0,tzinfo=TZ),
                'activity_not_work':datetime(2026,10,25,15,10,tzinfo=TZ)}
client=LocalModel()
output=Path('test-results');output.mkdir(exist_ok=True)
records=[]
for name,text,expected in cases:
    with tempfile.TemporaryDirectory(dir=output) as temp:
        store=Store(Path(temp)/'events.sqlite',FixedClock())
        source=store.source(text,'user-regression/'+name)
        if expected!='ignore':source['user_requested_event']=True
        try:
            proposals=client.analyze(source,[])
            messages=store.ingest(proposals,source)
            actual='event' if store.events() else 'pending' if store.pending() else 'ignore'
            rec={'case':name,'input':text,'expected':expected,'actual':actual,'passed':actual==expected,
                 'proposals':proposals,'messages':messages,'telemetry':client.telemetry,
                 'events':store.events()}
            if name in expected_times:
                rec['passed']=rec['passed'] and len(store.events())==1 and parse_time(store.events()[0]['time'])==expected_times[name]
        except Exception as exc:rec={'case':name,'input':text,'passed':False,'error':str(exc)}
        records.append(rec);store.close()
        print(json.dumps(rec,ensure_ascii=True),flush=True)
report={'results':records,'passed':sum(r['passed'] for r in records),'total':len(records)}
(output/(sys.argv[1] if len(sys.argv)>1 else 'activity-input-report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
sys.exit(0 if report['passed']==report['total'] else 1)
