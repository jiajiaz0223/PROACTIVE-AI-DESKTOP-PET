"""Explicit local file imports. Calendar subset fails closed on recurrence."""
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
import re
from proactive_pet.core import TZ


def read_source(path, store):
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('單檔上限 1MB，請拆分資料。')
    if path.suffix.lower() == '.eml':
        msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        body = msg.get_body(preferencelist=('plain',)) if msg.is_multipart() else msg
        if body is None or body.get_content_type() != 'text/plain':
            raise ValueError('目前只匯入含純文字本文的 EML，請另存文字版本。')
        text = 'Subject: ' + str(msg.get('subject', '')) + '\n' + body.get_content()
        timestamp = parsedate_to_datetime(msg['date']) if msg.get('date') else datetime.fromtimestamp(path.stat().st_mtime, TZ)
        timestamp = timestamp.replace(tzinfo=TZ) if timestamp.tzinfo is None else timestamp.astimezone(TZ)
    else:
        text = path.read_text(encoding='utf-8-sig')
        timestamp = datetime.fromtimestamp(path.stat().st_mtime, TZ)
    return store.source(text, str(path.resolve()), timestamp)


def calendar_items(text):
    text = re.sub(r'\r?\n[ \t]', '', text)
    results = []
    for block in text.split('BEGIN:VEVENT')[1:]:
        block = block.split('END:VEVENT')[0]
        fields = {}
        for line in block.splitlines():
            if ':' in line:
                key, val = line.split(':', 1)
                fields[key] = val
        def value(name):
            return next((v for k,v in fields.items() if k.split(';')[0] == name), '')
        if value('RRULE') or value('RECURRENCE-ID') or value('RDATE'):
            raise ValueError('目前不支援重複或例外行程；請匯出單次事件。')
        key = next((k for k in fields if k.split(';')[0] == 'DTSTART'), '')
        raw = fields.get(key, '')
        if 'VALUE=DATE' in key or len(raw) == 8:
            raise ValueError('全天事件沒有確定提醒時間，請手動新增時間。')
        if ';TZID=' in key and key.split(';TZID=')[1] not in ('Asia/Taipei','Asia/Shanghai'):
            raise ValueError('目前支援 UTC、Asia/Taipei 與 Asia/Shanghai 日曆時間。')
        cancelled = value('STATUS') == 'CANCELLED'
        dt = None
        if raw:
            fmt = '%Y%m%dT%H%M%S' if len(raw.rstrip('Z')) == 15 else '%Y%m%dT%H%M'
            dt = datetime.strptime(raw.rstrip('Z'), fmt).replace(tzinfo=timezone.utc if raw.endswith('Z') else TZ).astimezone(TZ)
        if not dt and not cancelled:
            raise ValueError('日曆缺少有效 DTSTART。')
        unescape = lambda s: s.replace('\\n','\n').replace('\\,',',').replace('\\;', ';').replace('\\\\','\\')
        results.append({'uid': value('UID'), 'title': unescape(value('SUMMARY')),
                        'time': dt.isoformat() if dt else None,
                        'location': unescape(value('LOCATION')), 'cancelled': cancelled})
    if not results:
        raise ValueError('檔案中沒有 VEVENT 事件。')
    return results


def calendar_proposals(text, events):
    proposals = []
    for item in calendar_items(text):
        key = 'calendar:' + item['uid'] if item['uid'] else None
        matches = [e for e in events if key and any(s.get('calendar_uid') == key for s in e['sources'])]
        old = matches[0] if len(matches) == 1 else None
        proposals.append({'action': 'cancel' if item['cancelled'] else ('update' if old else 'create'),
                          'target_event_id': old['id'] if old else None,
                          'title': item['title'], 'time': item['time'], 'location': item['location'],
                          'preparations': [], 'calendar_uid': key})
    return proposals
