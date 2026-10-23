"""Create fresh user-readable demo files outside the watched inbox."""
from pathlib import Path
from datetime import timedelta
from email.utils import format_datetime
from proactive_pet.core import local_now

root=Path(__file__).resolve().parent/'demo_samples'
root.mkdir(exist_ok=True)
now=local_now()
at=(now+timedelta(minutes=8)).replace(second=0,microsecond=0)
(root/'interview.eml').write_text(
    'From: demo@example.invalid\nTo: local@example.invalid\nSubject: Interview invitation\n'
    +'Date: '+format_datetime(now)+'\nContent-Type: text/plain; charset=utf-8\n\n'
    +f'Your Acme interview is on {at.strftime("%Y-%m-%d at %H:%M")} in Office B. Please bring your portfolio.\n',encoding='utf-8')
(root/'meeting.txt').write_text('五分鐘後要開專題會議，請先準備簡報。',encoding='utf-8')
(root/'calendar.ics').write_text('BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:demo-interview-'+now.strftime('%Y%m%d%H%M%S')
    +'\nDTSTART;TZID=Asia/Taipei:'+at.strftime('%Y%m%dT%H%M%S')+'\nSUMMARY:本機日曆測試\nLOCATION:Office B\nEND:VEVENT\nEND:VCALENDAR\n',encoding='utf-8')
print('Fresh samples: '+str(root))
