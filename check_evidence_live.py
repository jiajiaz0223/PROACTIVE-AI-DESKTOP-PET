from pathlib import Path
from datetime import datetime,timedelta
import tempfile,json
from proactive_pet.ai.local_model import LocalModel
from proactive_pet.core import Store,TZ,parse_time

class FixedClock:
    def now(self):return datetime(2026,10,25,15,0,tzinfo=TZ)

cases=[
    ('user_exact','三十分鐘後在A辦公室參加設計師面試，請準備作品集。'),
    ('screenshot_spaces','三十分鐘後在 A 辦公室參加設計師面試，請準備作品集。'),
    ('ascii_punctuation','三十分鐘後在A辦公室參加設計師面試,請準備作品集.'),
    ('line_break','三十分鐘後在A辦公室參加設計師面試，\n請準備作品集。'),
]
output=Path('test-results');output.mkdir(exist_ok=True)
client=LocalModel();records=[]
for name,text in cases:
    with tempfile.TemporaryDirectory(dir=output) as temp:
        store=Store(Path(temp)/'events.sqlite',FixedClock())
        source=store.source(text,'evidence-regression/'+name);source['user_requested_event']=True
        try:
            proposals=client.analyze(source,[])
            messages=store.ingest(proposals,source);events=store.events()
            ok=len(events)==1 and not store.pending() and parse_time(events[0]['time'])==store.clock.now()+timedelta(minutes=30)
            ok=ok and '面試' in events[0]['title'] and any('作品集' in s for s in events[0]['preparations'])
            ok=ok and proposals[0]['evidence'] in text
            record={'case':name,'input':text,'passed':ok,'messages':messages,'proposals':proposals,
                    'raw':source.get('model_analysis'),'telemetry':dict(client.telemetry)}
        except Exception as exc:record={'case':name,'input':text,'passed':False,'error':str(exc)}
        records.append(record);store.close()
        print(json.dumps({'case':name,'passed':record['passed']},ensure_ascii=True),flush=True)
report={'passed':sum(x['passed'] for x in records),'total':len(records),'results':records}
(output/'evidence-live-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(0 if report['passed']==report['total'] else 1)
