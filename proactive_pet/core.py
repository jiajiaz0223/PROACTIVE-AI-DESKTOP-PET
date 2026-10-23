"""Local event store and deterministic reminder policy. No model calls here."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=8), 'Asia/Taipei')


def local_now():
    return datetime.now(TZ)


def parse_time(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return (dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ))


def normalized(value):
    return ''.join(value.lower().split())


class Clock:
    def __init__(self, demo=False):
        self.demo = demo
        self.offset = timedelta()

    def now(self):
        return local_now() + self.offset

    def advance(self, seconds):
        if not self.demo:
            raise ValueError('真實時間模式不能快轉。')
        self.offset += timedelta(seconds=max(0, seconds))


class Store:
    def __init__(self, path, clock=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock or Clock()
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pending(id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS triggers(id TEXT PRIMARY KEY,event_id TEXT NOT NULL,
                due TEXT NOT NULL,phase TEXT NOT NULL,status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        ''')
        self.settings = {'quiet': False, 'quiet_start': 22, 'quiet_end': 8,
                         'lead_minutes': 1, 'max_count': 3, 'min_spacing': 30}
        for row in self.db.execute('SELECT * FROM settings'):
            self.settings[row['key']] = json.loads(row['value'])

    def close(self):
        self.db.close()

    def set_setting(self, key, value):
        self.settings[key] = value
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))

    def _rows(self, table):
        return [json.loads(r['data']) for r in self.db.execute(f'SELECT data FROM {table}')]

    def events(self, active=False):
        result = self._rows('events')
        if active:
            result = [e for e in result if e['status'] == 'active' and parse_time(e['time']) > self.clock.now()]
        return sorted(result, key=lambda e: e['time'])

    def event(self, eid):
        r = self.db.execute('SELECT data FROM events WHERE id=?', (eid,)).fetchone()
        return json.loads(r[0]) if r else None

    def _put(self, table, obj):
        self.db.execute(f'INSERT OR REPLACE INTO {table} VALUES (?,?)',
                        (obj['id'], json.dumps(obj, ensure_ascii=False)))

    def source(self, content, label, timestamp=None):
        # Same source content is idempotent across restarts. A changed file gets a new ID.
        sid = hashlib.sha256((label + '\0' + content).encode()).hexdigest()
        return {'id': sid, 'content': content, 'label': label,
                'timestamp': (timestamp or self.clock.now()).isoformat()}

    def seen(self, sid):
        return self.db.execute('SELECT 1 FROM sources WHERE id=?', (sid,)).fetchone() is not None

    def pending(self):
        return self._rows('pending')

    def remove_pending(self, pid):
        with self.db:
            self.db.execute('DELETE FROM pending WHERE id=?', (pid,))

    def ingest(self, proposals, source):
        if self.seen(source['id']):
            return ['相同內容已處理，沒有重複建立提醒。']
        messages = []
        with self.db:
            for proposal in proposals:
                try:
                    messages.append(self._apply(proposal, source))
                except (ValueError, TypeError, KeyError) as exc:
                    self._put('pending', {'id': uuid.uuid4().hex, 'proposal': proposal,
                              'source': source, 'reason': str(exc)})
                    messages.append('待確認：' + str(exc))
            self._put('sources', source)
        return messages

    def _apply(self, p, source):
        action = p.get('action')
        if action == 'ignore':
            return '未發現需要提醒的約定。'
        if action not in ('create', 'update', 'cancel'):
            raise ValueError('無法判斷是新增、改期還是取消。')
        if p.get('needs_review'):
            raise ValueError(p.get('reason') or '資訊有歧義，請確認。')
        eid = p.get('target_event_id')
        old = self.event(eid) if eid else None
        if action in ('update', 'cancel') and (not old or old['status'] != 'active'):
            raise ValueError('找不到唯一的原事件；請先選取要更新的事件。')
        if action == 'cancel':
            old['status'] = 'cancelled'
            old['sources'].append(source)
            self._put('events', old)
            self.db.execute("UPDATE triggers SET status='cancelled' WHERE event_id=? AND status='pending'", (eid,))
            return '已取消：' + old['title']
        title = (p.get('title') or (old or {}).get('title') or '').strip()
        if not title:
            raise ValueError('缺少事件名稱。')
        when = p.get('time')
        if p.get('relative_minutes') is not None:
            when = (parse_time(source['timestamp']) + timedelta(minutes=p['relative_minutes'])).isoformat()
        elif p.get('shift_minutes') is not None:
            if old is None:
                raise ValueError('需要先選取要延後或提前的事件。')
            when = (parse_time(old['time']) + timedelta(minutes=p['shift_minutes'])).isoformat()
        if not when:
            when = (old or {}).get('time')
        if not when:
            raise ValueError('缺少確定的日期或時間。')
        dt = parse_time(when)
        if dt <= self.clock.now():
            raise ValueError('時間已經過去，請確認日期；系統不會自動改成下週。')
        location = p.get('location')
        if action == 'create':
            # Exact title + instant; conflicting locations never merge automatically.
            matches = [e for e in self.events(active=True)
                       if normalized(e['title']) == normalized(title) and parse_time(e['time']) == dt
                       and (not location or not e['location'] or normalized(e['location']) == normalized(location))]
            if len(matches) == 1:
                old = matches[0]
        eid = old['id'] if old else uuid.uuid4().hex
        preps = list(dict.fromkeys((old or {}).get('preparations', []) + (p.get('preparations') or [])))
        event = {'id': eid, 'title': title, 'time': dt.isoformat(),
                 'location': location if location is not None else (old or {}).get('location'),
                 'preparations': preps, 'prep_done': (old or {}).get('prep_done', False),
                 'status': 'active', 'sources': (old or {}).get('sources', []) + [source]}
        self._put('events', event)
        self._schedule(event)
        return ('已更新：' if old else '已新增：') + title + ' ' + dt.strftime('%m/%d %H:%M')

    def manual(self, title, when, location='', preparations=None, eid=None):
        p = {'action': 'update' if eid else 'create', 'target_event_id': eid, 'title': title,
             'time': when, 'location': location, 'preparations': preparations or []}
        source = self.source('手動確認：' + json.dumps(p, ensure_ascii=False), '手動確認/' + uuid.uuid4().hex)
        with self.db:
            msg = self._apply(p, source)
            self._put('sources', source)
            if eid:
                e = self.event(eid)
                e['preparations'] = preparations or []
                self._put('events', e)
                self._schedule(e)
        return msg

    def quiet_adjust(self, dt):
        if not self.settings['quiet']:
            return dt
        start, end = self.settings['quiet_start'], self.settings['quiet_end']
        # Quiet period crosses midnight; move earlier, never after the event.
        if dt.hour >= start:
            return dt.replace(hour=start, minute=0, second=0, microsecond=0) - timedelta(minutes=1)
        if dt.hour < end:
            return (dt - timedelta(days=1)).replace(hour=start, minute=0, second=0, microsecond=0) - timedelta(minutes=1)
        return dt

    def _schedule(self, event):
        eid, now = event['id'], self.clock.now()
        self.db.execute("DELETE FROM triggers WHERE event_id=? AND status='pending'", (eid,))
        if event['status'] != 'active':
            return
        at = parse_time(event['time'])
        action = at - timedelta(minutes=int(self.settings['lead_minutes']))
        if action < now and at > now:
            action = now + timedelta(seconds=1)
        candidates = [('action', self.quiet_adjust(action))]
        if event['preparations'] and not event['prep_done']:
            prep = (at - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
            prep = self.quiet_adjust(prep)
            if (action - prep).total_seconds() >= int(self.settings['min_spacing']) * 60:
                candidates.insert(0, ('preparation', prep))
        already = self.db.execute("SELECT count(*) FROM triggers WHERE event_id=? AND status='fired'", (eid,)).fetchone()[0]
        for phase, due in candidates[:max(0, int(self.settings['max_count']) - already)]:
            if now <= due < at:
                if self.db.execute("SELECT 1 FROM triggers WHERE event_id=? AND phase=? AND due=? AND status='fired'", (eid,phase,due.isoformat())).fetchone():
                    continue
                self.db.execute('INSERT INTO triggers VALUES (?,?,?,?,?)',
                                (uuid.uuid4().hex, eid, due.isoformat(), phase, 'pending'))

    def replan_all(self):
        with self.db:
            for e in self.events(active=True):
                self._schedule(e)

    def mark(self, eid, status):
        e = self.event(eid)
        if not e:
            return
        with self.db:
            if status == 'prep_done':
                e['prep_done'] = True
                self.db.execute("UPDATE triggers SET status='cancelled' WHERE event_id=? AND phase='preparation' AND status='pending'", (eid,))
            else:
                e['status'] = status
                self.db.execute("UPDATE triggers SET status='cancelled' WHERE event_id=? AND status='pending'", (eid,))
            self._put('events', e)

    def triggers(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM triggers WHERE status='pending' ORDER BY due")]

    def snooze(self, tid, minutes=15):
        r = self.db.execute('SELECT * FROM triggers WHERE id=?', (tid,)).fetchone()
        if not r:
            raise ValueError('找不到提醒。')
        e = self.event(r['event_id'])
        if e['status'] != 'active' or (r['phase'] == 'preparation' and e['prep_done']):
            raise ValueError('此事件或準備提醒已結束。')
        count = self.db.execute("SELECT count(*) FROM triggers WHERE event_id=? AND status='fired'", (e['id'],)).fetchone()[0]
        if count >= self.settings['max_count']:
            raise ValueError('已達此事件的提醒上限。')
        due = self.quiet_adjust(self.clock.now() + timedelta(minutes=minutes))
        if not self.clock.now() < due < parse_time(e['time']):
            raise ValueError('延後時間超過事件開始時間或落在安靜時段；請修正事件時間。')
        with self.db:
            # Repeated clicks on the same reminder replace the same snooze.
            self.db.execute('INSERT OR REPLACE INTO triggers VALUES (?,?,?,?,?)',
                            (tid + '_snooze', e['id'], due.isoformat(), r['phase'], 'pending'))

    def tick(self):
        now, fired = self.clock.now(), []
        with self.db:
            for t in self.triggers():
                if parse_time(t['due']) > now:
                    continue
                e = self.event(t['event_id'])
                quiet = self.settings['quiet'] and (now.hour >= self.settings['quiet_start'] or now.hour < self.settings['quiet_end'])
                count = self.db.execute("SELECT count(*) FROM triggers WHERE event_id=? AND status='fired'", (e['id'],)).fetchone()[0]
                valid = (e['status'] == 'active' and parse_time(e['time']) > now and not quiet
                         and not (t['phase'] == 'preparation' and e['prep_done'])
                         and count < self.settings['max_count']
                         and (now - parse_time(t['due'])).total_seconds() <= 900)
                self.db.execute('UPDATE triggers SET status=? WHERE id=?', ('fired' if valid else 'skipped', t['id']))
                if valid:
                    fired.append((t, e))
        return fired
