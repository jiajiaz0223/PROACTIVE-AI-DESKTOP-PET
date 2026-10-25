import tempfile,unittest,tkinter as tk
from pathlib import Path
from proactive_pet.core import Store
from proactive_pet.ui.app import Application
from test_core import FakeClock

class ActivityLogTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[1]/'test-results';base.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base)
    def tearDown(self):self.temp.cleanup()
    def test_persisted_order_includes_date_and_exact_message(self):
        path=Path(self.temp.name)/'log.sqlite';clock=FakeClock()
        store=Store(path,clock)
        store.append_log('建立：面試');clock.advance(86400);store.append_log('完成：面試');store.close()
        store=Store(path,clock)
        try:
            rows=store.activity_log()
            self.assertEqual([x['message'] for x in rows],['建立：面試','完成：面試'])
            self.assertTrue(rows[0]['timestamp'].startswith('2026-10-12'))
            self.assertTrue(rows[1]['timestamp'].startswith('2026-10-13'))
        finally:store.close()
    def test_ui_restores_history_without_creating_duplicate_rows(self):
        project=Path(self.temp.name);data=project/'data'
        store=Store(data/'demo.sqlite',FakeClock());store.append_log('已新增：設計師面試');store.close()
        root=tk.Tk();root.withdraw();app=Application(root,project,True,data);app.pet.window.withdraw()
        try:
            self.assertIn('10/12 12:00:00 已新增：設計師面試',app.logbox.get('1.0','end'))
            app.log('查看原文：設計師面試')
            self.assertEqual(len(app.store.activity_log()),2)
        finally:app.close()

if __name__=='__main__':unittest.main()
