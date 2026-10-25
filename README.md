# 呱呱 · Proactive AI Desktop Pet
A local AI desktop companion that turns messages into persistent reminders.

## 在這台電腦開始使用
1. 雙擊 `Start-Pet.cmd`。
2. 確認模型狀態顯示「模型已就緒：qwen3:4b」。
3. 輸入「五分鐘後要開專題會議，請先準備簡報。」並按「整理成行程 →」。
4. 事件會出現在清單；預設開始前 1 分鐘自動提醒。
5. 要改期，選取事件、勾選「更新選取的事件」，輸入「剛才的專題會議延後十分鐘」。
6. 可用中文取消、手動修正時間、標記準備完成、完成事件、延後提醒或查看原文。

## 功能範圍
- 真實 Ollama 本機模型，預設 Qwen3 4B；沒有關鍵字規則冒充 AI。
- AI 分析在背景執行，視窗及排程持續回應。
- 結構化事件檢查、模糊／過期資訊進待確認清單。
- SQLite 保存事件、來源、待確認項與提醒狀態；重啟可恢復。
- 保守合併：相同名稱、時間與不衝突地點；改期使用明確事件 ID。
- 自動提醒，22:00–08:00 可選安靜時段；準備與開始提醒至少間隔 30 分鐘。
- 每事件最多 3 次已送達提醒（包含稍後提醒）。手動延後為真實模式 15 分鐘／展示模式 1 分鐘。
- TXT、純文字 EML、單次 ICS 匯入；監看專案 inbox 的新內容。
- 獨立展示模式：獨立資料庫、快轉時鐘、相同排程流程。
- 本機事件紀錄匯出；只回報實測分析時間，不宣稱未量測的功耗。
- Hailo-Ollama 接口可設定；UGen300 實機尚未驗證。

## 本機安裝與啟動
Python 3.10+（含 tkinter）。應用程式不需要額外 Python 套件。
初次安裝本機模型（需網路與數 GB 磁碟空間）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_local_model.ps1
python run_pet.py
```

Ollama 可攜版放在 `.runtime/ollama`，模型放在 `.runtime/models`。
服務只綁定 `127.0.0.1:11435`，設定 `OLLAMA_NO_CLOUD=1`。
程式會自動啟動專案本機服務；不修改系統預設模型服務。
模型載入失敗時明確顯示錯誤，不使用模擬結果替代。

## 真實資料與展示資料
- `data/events.sqlite`：日常事件。
- `data/demo.sqlite`：展示事件。
- `inbox/`：日常監看資料夾；`demo_inbox/`：展示監看資料夾。
- `python make_demo_sources.py`：產生時間新鮮的 TXT／EML／ICS 範例到 `demo_samples/`，再自行匯入。
- 原有 `fixtures/` 為歷史範例，日期可能已過；不會偷偷改成未來。
- 不同模式各允許一個執行個體，避免重複通知。
- 初次從模型開機載入可能較慢；熱啟動效能請以實測報告為準。

## 測試
```powershell
python run_checks.py
python run_checks.py --model
```
第一個命令只測試事件與排程；第二個額外呼叫真實本機模型。
測試失敗會回傳非零狀態，不固定印出 PASS。
模型報告輸出至 `test-results/live-model-report.json`。
模型測試阻擋 Python 測試程序的非 loopback 連線；不是關閉 Windows 網卡的測試。

## 限制
- 電腦與程式須保持運作。重新開啟只補發 15 分鐘內、尚未開始的事件提醒；更舊或已過期提醒略過。
- 資料保存在本機，但未加密；目前沒有雲端同步、Gmail／Teams／Slack OAuth 連接器。
- ICS 支援單次事件、UTC／台北／上海／本機浮動時間；重複、全天和其他時區需先轉換或手動確認。
- 模型仍可能判斷錯誤。請從來源檢查結果，重要事件可手動修正。
- 台北為固定時區；跨時區旅行和多裝置同步尚未實作。
- 安靜時段把提醒往前移，若可用時間已過則不安排；清單的「下一次提醒」會顯示空白。
- 本機 GPU 推論完成不代表完成 UGen300 實機驗證。參見 docs/HARDWARE_UGEN300.md。

## Competition positioning
Workplace AI / Lightweight track. Demonstrate: ingest, local understanding,
validated event, automatic reminder, reschedule/cancel, restart continuity.
Business value and pricing remain hypotheses; see docs/BUSINESS_PLAN.md.
