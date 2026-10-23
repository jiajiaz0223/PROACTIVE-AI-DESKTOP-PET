"""Real local model evaluation. Never run this as a simulated unit test."""
import json
import socket
import sys
from pathlib import Path
from datetime import datetime, timedelta
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from proactive_pet.core import Store, TZ, parse_time
from proactive_pet.ai.local_model import LocalModel


def run(model='qwen3:4b',endpoint='http://127.0.0.1:11435'):
    # Blocks non-loopback Python connections; does not disable the OS network adapter.
    original=socket.socket.connect
    def local_only(sock,address):
        if isinstance(address,tuple) and address[0] not in ('127.0.0.1','::1','localhost'):
            raise RuntimeError('Non-local network access blocked during this test')
        return original(sock,address)
    socket.socket.connect=local_only
    client=LocalModel(model,endpoint)
    anchor=datetime(2026,10,12,12,0,tzinfo=TZ)
    class FixedClock:
        def now(self):return anchor
    root=ROOT/'test-results';root.mkdir(exist_ok=True)
    records=[]
    try:
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            store=Store(Path(tmp)/'live.sqlite',FixedClock())
            def check(name,text,predicate,context=None,selected=None):
                source=store.source(text,'live-test/'+name,anchor)
                try:
                    p=client.analyze(source,context or [],selected)
                    ok=bool(predicate(p))
                    record={'case':name,'passed':ok,'proposals':p,'telemetry':dict(client.telemetry)}
                except Exception as exc:
                    p=[];record={'case':name,'passed':False,'error':str(exc)}
                records.append(record)
                print(json.dumps(record,ensure_ascii=False),flush=True)
                return source,p
            s,p=check('Chinese relative commitment','五分鐘後要開專題會議，請先準備簡報。',
                lambda p:len(p)==1 and p[0]['action']=='create' and p[0]['relative_minutes']==5 and not p[0]['needs_review'] and any('簡報' in x for x in p[0]['preparations']))
            store.ingest(p,s)
            events=store.events()
            if events:
                e=events[0]
                s,p=check('Selected event reschedule','剛才的專題會議延後十分鐘。',
                    lambda p:len(p)==1 and p[0]['action']=='update' and p[0]['target_event_id']==e['id'] and p[0]['shift_minutes']==10 and not p[0]['needs_review'],events,e['id'])
                store.ingest(p,s)
                s,p=check('Selected event cancellation','取消剛才的專題會議。',
                    lambda p:len(p)==1 and p[0]['action']=='cancel' and p[0]['target_event_id']==e['id'] and not p[0]['needs_review'],store.events(),e['id'])
                store.ingest(p,s)
            check('Explicit date and morning hour','Your interview with Acme is Friday, October 16, 2026 at 9:00 AM in Office B. Bring your portfolio.',
                lambda p:len(p)==1 and p[0]['action']=='create' and parse_time(p[0]['time'])==datetime(2026,10,16,9,tzinfo=TZ) and p[0]['location']=='Office B')
            check('Tomorrow afternoon','明天下午三點到台大圖書館討論專題，請帶筆電。',
                lambda p:len(p)==1 and parse_time(p[0]['time'])==datetime(2026,10,13,15,tzinfo=TZ) and any('筆電' in x for x in p[0]['preparations']))
            check('Missing time stays pending','我們改天一起討論專題。',lambda p:not p or all(x['action']=='ignore' or x['needs_review'] for x in p))
            check('Advertisement ignored','本週披薩全面五折！點我領取優惠。',lambda p:not p or all(x['action']=='ignore' for x in p))
            check('Distinct appointments','明天下午一點與甲公司面試，下午兩點與乙公司面試。',
                lambda p:len(p)==2 and sorted(parse_time(x['time']).hour for x in p)==[13,14] and p[0]['title']!=p[1]['title'])
            store.close()
    finally:
        socket.socket.connect=original
    report={'model':model,'external_connections':'blocked in Python test process',
            'physical_network_adapter_disabled':False,'results':records,
            'passed':sum(r['passed'] for r in records),'total':len(records)}
    (root/'live-model-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    report=run()
    sys.exit(0 if report['passed']==report['total'] and report['total']==8 else 1)
