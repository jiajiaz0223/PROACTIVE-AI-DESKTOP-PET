"""Traditional Chinese desktop workflow. Model work stays off the Tk thread."""
from __future__ import annotations
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import timedelta

from proactive_pet.core import Store, Clock, parse_time
from proactive_pet.ai.local_model import LocalModel
from proactive_pet.ingestion.files import read_source, calendar_proposals


class Pet:
    def __init__(self, app):
        self.app, self.current = app, None
        self.window = tk.Toplevel(app.root)
        self.window.title('呱呱 · 本機提醒')
        self.window.attributes('-topmost', True)
        self.window.geometry(f'380x300+{max(0,app.root.winfo_screenwidth()-410)}+{max(0,app.root.winfo_screenheight()-390)}')
        self.window.configure(bg='#12362f')
        self.window.protocol('WM_DELETE_WINDOW', self.window.withdraw)
        self.canvas = tk.Canvas(self.window, height=82, bg='#12362f', highlightthickness=0)
        self.canvas.pack(fill='x')
        self.canvas.create_oval(135, 23, 245, 78, fill='#86d9a0', outline='')
        for x in (151,217):
            self.canvas.create_oval(x-14, 9, x+14, 38, fill='#86d9a0', outline='')
            self.canvas.create_oval(x-5, 17, x+5, 29, fill='#12362f', outline='')
        self.canvas.create_arc(168, 37, 213, 64, start=180, extent=180, style='arc', width=3)
        self.text = tk.Label(self.window, text='我會在時間到時提醒你。\n先加入一個事件吧！',
                             wraplength=340, font=('Microsoft JhengHei UI',12), bg='#12362f', fg='white', justify='left')
        self.text.pack(padx=16, pady=8, fill='x')
        self.info = tk.Label(self.window, text='', bg='#12362f', fg='#a1cfbd', wraplength=340)
        self.info.pack(padx=12)
        row = ttk.Frame(self.window)
        row.pack(padx=12, pady=12, fill='x')
        for text, cmd in [('查看來源', self.details),('稍後提醒', self.snooze),('準備完成', self.prepared),('下一則', self.next)]:
            ttk.Button(row,text=text,command=cmd).pack(side='left',expand=True)

    def show(self, trigger, event):
        self.current = (trigger,event)
        remain = max(0, int((parse_time(event['time'])-self.app.clock.now()).total_seconds()/60))
        prep = '、'.join(event['preparations']) or '查看事件細節'
        self.text.config(text=f"{event['title']}\n{parse_time(event['time']).strftime('%m/%d %H:%M')} · 約 {remain} 分鐘後\n" +
                         (f'準備：{prep}' if not event['prep_done'] else '準備已完成。'))
        self.info.config(text=f"{event['location'] or '未指定地點'} · {'展示時間' if self.app.clock.demo else '真實時間'}")
        self.window.deiconify()
        self.window.lift()
        self.window.bell()

    def details(self):
        if self.current:
            self.app.details(self.current[1]['id'])

    def snooze(self):
        if not self.current:
            return
        try:
            self.app.store.snooze(self.current[0]['id'], 1 if self.app.clock.demo else 15)
            self.app.log('已延後提醒。')
            self.next()
        except ValueError as exc:
            messagebox.showinfo('無法延後', str(exc), parent=self.window)

    def prepared(self):
        if self.current:
            self.app.store.mark(self.current[1]['id'], 'prep_done')
            self.app.log('已標記準備完成，保留開始前提醒。')
            self.next()
            self.app.refresh()

    def next(self):
        self.current = None
        self.text.config(text='持續留意你的行程。')
        self.app.display_next()


class Application:
    def __init__(self, root, project, demo=False, data_dir=None):
        self.root, self.project = root, Path(project)
        self.clock = Clock(demo)
        self.data_dir = Path(data_dir or self.project/'data')
        self.store = Store(self.data_dir/('demo.sqlite' if demo else 'events.sqlite'), self.clock)
        self.inbox = self.project/('demo_inbox' if demo else 'inbox')
        self.inbox.mkdir(exist_ok=True)
        self.messages, self.notifications, self.jobs = queue.Queue(), [], []
        self.busy, self.closing, self.failed_files, self.queued_ids = False, False, {}, set()
        self.root.title('呱呱 · 本機 AI 行程助理' + ('【加速展示】' if demo else ''))
        width, height = min(1180,root.winfo_screenwidth()-60), min(850,root.winfo_screenheight()-100)
        self.root.geometry(f'{width}x{height}+25+25')
        self.root.minsize(880,650)
        self.root.option_add('*Font', ('Microsoft JhengHei UI',10))
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TButton', padding=(10,6))
        style.configure('Treeview', rowheight=30)
        style.configure('Header.TLabel',font=('Microsoft JhengHei UI',20,'bold'))
        self.build()
        self.pet = Pet(self)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh()
        self.root.after(250, self.pump)
        self.root.after(500, self.check_model)
        self.root.after(3000, self.watch)

    def build(self):
        frame = ttk.Frame(self.root,padding=18)
        frame.pack(fill='both',expand=True)
        header = ttk.Frame(frame); header.pack(fill='x')
        ttk.Label(header,text='呱呱 · 讓約定不被漏掉',style='Header.TLabel').pack(side='left')
        self.clock_label=ttk.Label(header); self.clock_label.pack(side='right')
        ttk.Label(frame,text='本機分析 · 原文可追溯 · 到點自動提醒' + ('  |  展示資料獨立保存' if self.clock.demo else '' )).pack(anchor='w',pady=(3,12))
        settings=ttk.LabelFrame(frame,text='本機模型與提醒偏好',padding=8); settings.pack(fill='x')
        self.backend=tk.StringVar(value=self.store.settings.get('backend','ollama'))
        ttk.Combobox(settings,textvariable=self.backend,values=['ollama','hailo'],width=9,state='readonly').grid(row=0,column=0,padx=3)
        self.endpoint=tk.StringVar(value=self.store.settings.get('endpoint','http://127.0.0.1:11435'))
        ttk.Entry(settings,textvariable=self.endpoint,width=28).grid(row=0,column=1,padx=3)
        self.model_name=tk.StringVar(value=self.store.settings.get('model','qwen3:4b'))
        ttk.Entry(settings,textvariable=self.model_name,width=18).grid(row=0,column=2,padx=3)
        ttk.Button(settings,text='檢查並儲存',command=self.check_model).grid(row=0,column=3,padx=3)
        self.model_status=ttk.Label(settings,text='正在檢查模型…'); self.model_status.grid(row=1,column=0,columnspan=5,sticky='w',pady=5)
        pref=ttk.Frame(settings);pref.grid(row=2,column=0,columnspan=5,sticky='w')
        ttk.Label(pref,text='開始前提醒（分鐘）').pack(side='left')
        self.lead=tk.IntVar(value=self.store.settings['lead_minutes'])
        ttk.Spinbox(pref,from_=1,to=1440,textvariable=self.lead,width=5).pack(side='left',padx=4)
        self.quiet=tk.BooleanVar(value=self.store.settings['quiet'])
        ttk.Checkbutton(pref,text='22:00–08:00 安靜時段',variable=self.quiet).pack(side='left',padx=8)
        ttk.Button(pref,text='套用提醒偏好',command=self.save_preferences).pack(side='left')
        ttk.Button(pref,text='顯示寵物',command=lambda:self.pet.window.deiconify()).pack(side='left',padx=6)
        notebook=ttk.Notebook(frame);notebook.pack(fill='both',expand=True,pady=12)
        main=ttk.Frame(notebook,padding=10);notebook.add(main,text='行程與輸入')
        self.input=scrolledtext.ScrolledText(main,height=3,wrap='word',font=('Microsoft JhengHei UI',11))
        self.input.pack(fill='x')
        self.input.insert('1.0','五分鐘後要開專題會議，請先準備簡報。')
        toolbar=ttk.Frame(main);toolbar.pack(fill='x',pady=6)
        self.analyze_button=ttk.Button(toolbar,text='用本機 AI 分析',command=self.submit);self.analyze_button.pack(side='left')
        ttk.Button(toolbar,text='手動新增',command=lambda:self.editor()).pack(side='left',padx=4)
        ttk.Button(toolbar,text='匯入 TXT / EML / ICS',command=self.import_files).pack(side='left',padx=4)
        self.use_selected=tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar,text='這段訊息更新選取的事件',variable=self.use_selected).pack(side='left',padx=8)
        self.watch_enabled=tk.BooleanVar(value=True)
        ttk.Checkbutton(main,text=f'自動讀取專案 {self.inbox.name} 資料夾的新檔案（TXT／EML／ICS）',variable=self.watch_enabled).pack(anchor='w')
        columns=('title','time','location','status','next')
        self.tree=ttk.Treeview(main,columns=columns,show='headings',selectmode='browse',height=5)
        for col,label,width in zip(columns,['事件','時間（台北）','地點','狀態','下一次提醒'],[230,150,130,100,150]):
            self.tree.heading(col,text=label); self.tree.column(col,width=width,minwidth=60)
        self.tree.pack(fill='both',expand=True,pady=8)
        self.tree.bind('<Double-1>',lambda e:self.details())
        actions=ttk.Frame(main);actions.pack(fill='x')
        for text,cmd in [('查看原文',self.details),('修正／改期',self.edit_selected),('準備完成',lambda:self.mark_selected('prep_done')),
                         ('完成事件',lambda:self.mark_selected('completed')),('取消事件',lambda:self.mark_selected('cancelled'))]:
            ttk.Button(actions,text=text,command=cmd).pack(side='left',padx=3)
        pending=ttk.Frame(notebook,padding=10);notebook.add(pending,text='待確認')
        ttk.Label(pending,text='缺少時間、已過期或關聯不明的內容，確認後才建立提醒。').pack(anchor='w')
        self.pending_list=tk.Listbox(pending,height=12);self.pending_list.pack(fill='both',expand=True,pady=8)
        prow=ttk.Frame(pending);prow.pack(fill='x')
        ttk.Button(prow,text='查看並確認',command=self.resolve_pending).pack(side='left')
        ttk.Button(prow,text='忽略此項',command=self.dismiss_pending).pack(side='left',padx=8)
        history=ttk.Frame(notebook,padding=10);notebook.add(history,text='執行紀錄')
        self.logbox=scrolledtext.ScrolledText(history,wrap='word',height=12,state='disabled');self.logbox.pack(fill='both',expand=True)
        ttk.Button(history,text='匯出本機事件與提醒紀錄',command=self.export).pack(anchor='w',pady=6)
        bottom=ttk.Frame(frame);bottom.pack(fill='x')
        self.summary=ttk.Label(bottom,text='就緒');self.summary.pack(side='left')
        if self.clock.demo:
            ttk.Button(bottom,text='快轉 1 分鐘',command=lambda:self.advance(60)).pack(side='right',padx=4)
            ttk.Button(bottom,text='前往下一次提醒',command=self.jump).pack(side='right',padx=4)
        else:
            ttk.Button(bottom,text='開啟獨立展示模式',command=self.open_demo).pack(side='right')

    def log(self,text):
        self.logbox.config(state='normal');self.logbox.insert('end',self.clock.now().strftime('%H:%M:%S')+' '+str(text)+'\n')
        self.logbox.see('end');self.logbox.config(state='disabled')

    def selected(self):
        s=self.tree.selection()
        return s[0] if s else None

    def model(self):
        return LocalModel(self.model_name.get().strip(),self.endpoint.get().strip(),self.backend.get())

    def check_model(self):
        try:
            client=self.model()
        except ValueError as exc:
            self.model_status.config(text=str(exc));return
        for k,v in [('model',client.model),('endpoint',client.base_url),('backend',client.backend)]:
            self.store.set_setting(k,v)
        self.model_status.config(text='檢查中…')
        def work():
            try:
                names=client.status()
                text=('模型已就緒：'+client.model) if client.model in names else ('服務可用，但尚未下載 '+client.model)
                self.messages.put(('status',text))
            except Exception as exc:
                self.messages.put(('status',str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def submit(self):
        text=self.input.get('1.0','end').strip()
        if not text:
            return
        selected=self.selected() if self.use_selected.get() else None
        if self.use_selected.get() and not selected:
            messagebox.showinfo('選取事件','請先選取要更新的事件。');return
        source=self.store.source(text,'手動輸入/'+self.clock.now().strftime('%Y-%m-%d %H:%M'))
        self.enqueue(source,selected)

    def enqueue(self,source,selected=None,path=None):
        if self.store.seen(source['id']) or source['id'] in self.queued_ids:
            self.log('相同來源內容已處理或正在處理。');return
        self.jobs.append((source,selected,path));self.queued_ids.add(source['id'])
        self.start_next()

    def start_next(self):
        if self.busy or not self.jobs:
            return
        source,selected,path=self.jobs.pop(0)
        try:
            client=self.model()
        except ValueError as exc:
            self.queued_ids.discard(source['id']);self.log(str(exc));return
        context=self.store.events(active=True)
        if selected:
            context.sort(key=lambda e:e['id']!=selected)
        self.busy=True;self.analyze_button.config(state='disabled')
        self.summary.config(text='本機模型分析中，提醒排程持續運作…')
        self.log('開始分析：'+source['label'])
        def work():
            try:
                p=client.analyze(source,context,selected)
                self.messages.put(('result',source,p,client.telemetry,path))
            except Exception as exc:
                self.messages.put(('error',source,str(exc),path))
        threading.Thread(target=work,daemon=True).start()

    def pump(self):
        if self.closing:
            return
        while not self.messages.empty():
            msg=self.messages.get()
            if msg[0]=='status':
                self.model_status.config(text=msg[1]);continue
            self.busy=False;self.analyze_button.config(state='normal');self.queued_ids.discard(msg[1]['id'])
            if msg[0]=='result':
                for line in self.store.ingest(msg[2],msg[1]):self.log(line)
                self.log(f"實測分析 {msg[3]['elapsed_ms']/1000:.2f} 秒 · {msg[3]['model']} · 功耗未量測")
            else:
                self.log('分析失敗，沒有建立提醒：'+msg[2])
                if msg[3]:self.failed_files[str(msg[3])]=msg[1]['id']
            self.refresh()
            self.start_next()
        for t,e in self.store.tick():
            self.notifications.append((t,e));self.log('自動提醒：'+e['title'])
        if self.pet.current:
            t,e=self.pet.current
            current=self.store.event(e['id'])
            if current['status']!='active' or current['time'] != e['time'] or (t['phase']=='preparation' and current['prep_done']):
                self.pet.next()
        self.display_next()
        self.clock_label.config(text=('展示 ' if self.clock.demo else '台北 ')+self.clock.now().strftime('%m/%d %H:%M:%S'))
        if not self.busy:
            self.summary.config(text=f'{len(self.store.events(active=True))} 個未來事件 · {len(self.store.triggers())} 個待觸發提醒 · {len(self.store.pending())} 項待確認')
        self.root.after(500,self.pump)

    def display_next(self):
        if self.pet.current:
            return
        while self.notifications:
            t,e=self.notifications.pop(0);current=self.store.event(e['id'])
            if current['status']=='active' and parse_time(current['time'])>self.clock.now():
                self.pet.show(t,current);break

    def refresh(self):
        selection=self.selected()
        for iid in self.tree.get_children():self.tree.delete(iid)
        pending=self.store.triggers()
        for e in self.store.events():
            next_t=next((t for t in pending if t['event_id']==e['id']),None)
            status={'active':'待進行','cancelled':'已取消','completed':'已完成'}[e['status']]
            if e['status']=='active' and parse_time(e['time'])<=self.clock.now():status='已過時間'
            if e['prep_done'] and status=='待進行':status='已備妥'
            self.tree.insert('',0,iid=e['id'],values=(e['title'],parse_time(e['time']).strftime('%m/%d %H:%M'),e['location'] or '—',status,
                parse_time(next_t['due']).strftime('%m/%d %H:%M') if next_t else '—'))
        if selection and self.tree.exists(selection):self.tree.selection_set(selection)
        self.pending_items=self.store.pending();self.pending_list.delete(0,'end')
        for p in self.pending_items:self.pending_list.insert('end',(p['proposal'].get('title') or '未命名')+' — '+p['reason'])

    def details(self,eid=None):
        e=self.store.event(eid or self.selected())
        if not e:return
        win=tk.Toplevel(self.root);win.title('事件與原文');win.geometry('650x500')
        box=scrolledtext.ScrolledText(win,wrap='word');box.pack(fill='both',expand=True)
        box.insert('end',f"{e['title']}\n{e['time']}\n地點：{e['location'] or '未指定'}\n準備：{'、'.join(e['preparations']) or '無'}\n")
        for s in e['sources']:box.insert('end',f"\n來源：{s['label']}\n收到時間：{s['timestamp']}\n{s['content']}\n")
        box.config(state='disabled')

    def editor(self,event=None,pending=None):
        e=event or (pending or {}).get('proposal',{})
        win=tk.Toplevel(self.root);win.title('確認事件');win.geometry('720x490');win.transient(self.root)
        win.columnconfigure(1,weight=1)
        vars={}
        for i,(key,label,default) in enumerate([
            ('title','事件名稱',e.get('title') or ''),('time','台北時間 YYYY-MM-DD HH:MM',e.get('time') or (self.clock.now()+timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M')),
            ('location','地點',e.get('location') or ''),('preparations','準備事項（以分號分隔）',';'.join(e.get('preparations') or []))]):
            ttk.Label(win,text=label).grid(row=i,column=0,sticky='w',padx=12,pady=8)
            vars[key]=tk.StringVar(value=default)
            ttk.Entry(win,textvariable=vars[key],width=30).grid(row=i,column=1,padx=10,pady=8,sticky='ew')
        if pending:
            box=scrolledtext.ScrolledText(win,height=8,wrap='word');box.grid(row=4,column=0,columnspan=2,padx=12,sticky='ew')
            box.insert('end',pending['reason']+'\n\n'+pending['source']['content']);box.config(state='disabled')
        def save():
            try:
                eid=event['id'] if event else None
                msg=self.store.manual(vars['title'].get(),vars['time'].get(),vars['location'].get(),
                    [s.strip() for s in vars['preparations'].get().split(';') if s.strip()],eid)
                if pending:
                    # Preserve the original evidence alongside the explicit correction.
                    target=next((x for x in reversed(self.store.events()) if x['title']==vars['title'].get() and parse_time(x['time'])==parse_time(vars['time'].get())),None)
                    if target:
                        target['sources'].append(pending['source'])
                        with self.store.db:self.store._put('events',target)
                    self.store.remove_pending(pending['id'])
                self.log(msg);self.refresh();win.destroy()
            except (ValueError,TypeError) as exc:messagebox.showerror('請修正內容',str(exc),parent=win)
        ttk.Button(win,text='儲存並排定提醒',command=save).grid(row=5,column=0,columnspan=2,pady=15)

    def edit_selected(self):
        e=self.store.event(self.selected())
        if e:self.editor(event=e)

    def mark_selected(self,status):
        eid=self.selected()
        if eid:self.store.mark(eid,status);self.refresh();self.log('已更新事件狀態。')

    def resolve_pending(self):
        s=self.pending_list.curselection()
        if not s:return
        p=self.pending_items[s[0]]
        if p['proposal'].get('action') in ('cancel','update'):
            messagebox.showinfo('請選取原事件','請回到行程頁選取原事件，再用修正／取消按鈕處理。處理後可忽略此待確認項。')
        else:self.editor(pending=p)

    def dismiss_pending(self):
        s=self.pending_list.curselection()
        if s:self.store.remove_pending(self.pending_items[s[0]]['id']);self.refresh()

    def import_path(self,path):
        source=read_source(path,self.store)
        if self.store.seen(source['id']) or source['id'] in self.queued_ids or self.failed_files.get(str(path))==source['id']:
            return
        if Path(path).suffix.lower()=='.ics':
            proposals=calendar_proposals(source['content'],self.store.events())
            # Keep separate source identity per UID, plus record whole import fingerprint.
            for p in proposals:
                part=dict(source,id=source['id']+':'+str(p.get('calendar_uid') or p['title']),calendar_uid=p.get('calendar_uid'))
                for line in self.store.ingest([p],part):self.log(line)
            with self.store.db:self.store._put('sources',source)
            self.refresh()
        else:self.enqueue(source,path=path)

    def import_files(self):
        for path in filedialog.askopenfilenames(filetypes=[('本機來源','*.txt *.eml *.ics')]):
            self.failed_files.pop(str(path),None)
            try:self.import_path(path)
            except Exception as exc:self.log('匯入失敗：'+str(exc))

    def watch(self):
        if self.closing:return
        if self.watch_enabled.get():
            for path in self.inbox.iterdir():
                if path.suffix.lower() not in ('.txt','.eml','.ics') or not path.is_file():continue
                try:self.import_path(path)
                except Exception as exc:
                    stamp=str(path.stat().st_mtime_ns)
                    if self.failed_files.get(str(path))!=stamp:self.log(path.name+'：'+str(exc));self.failed_files[str(path)]=stamp
        self.root.after(4000,self.watch)

    def save_preferences(self):
        try:
            lead=self.lead.get()
            if not 1<=lead<=1440:raise ValueError()
        except (ValueError,tk.TclError):messagebox.showerror('無效數值','提醒時間需介於 1–1440 分鐘。');return
        self.store.set_setting('lead_minutes',lead);self.store.set_setting('quiet',self.quiet.get())
        self.store.replan_all();self.refresh();self.log('已更新提醒偏好。安靜時段不補發已錯過的提醒。')

    def advance(self,seconds):
        self.clock.advance(seconds);self.refresh()

    def jump(self):
        triggers=self.store.triggers()
        if triggers:self.advance((parse_time(triggers[0]['due'])-self.clock.now()).total_seconds()+1)

    def open_demo(self):
        subprocess.Popen([sys.executable,str(self.project/'run_pet.py'),'--demo'],cwd=self.project,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    def export(self):
        path=filedialog.asksaveasfilename(defaultextension='.json',initialfile='pet-local-report.json')
        if path:
            report={'generated_at':self.clock.now().isoformat(),'demo':self.clock.demo,
                    'events':self.store.events(),'pending':self.store.pending(),
                    'triggers':[dict(r) for r in self.store.db.execute('SELECT * FROM triggers')]}
            Path(path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            self.log('已匯出本機紀錄。')

    def close(self):
        self.closing=True;self.store.close();self.root.destroy()
