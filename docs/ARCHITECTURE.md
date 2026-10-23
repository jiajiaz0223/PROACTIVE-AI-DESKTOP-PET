# Architecture
Local files / pasted text -> loopback model API -> validated proposals ->
SQLite events and sources -> deterministic reminder policy -> persistent triggers -> desktop pet.

## Separation of responsibility
The language model interprets text. core.Store validates time and event references,
merges only exact conservative matches, stores state, and builds bounded reminders.
The GUI calls Store.tick every 500ms. Model inference runs in a background thread;
only the GUI thread accesses the SQLite connection.
The inbox scan runs every 4 seconds and hashes source content. Identical content is idempotent.

## Sources and updates
EML relative dates anchor to its Date header; TXT uses file modification time;
pasted text uses the application clock. Explicit dates take precedence.
Ambiguous or past events go to pending review. Updates and cancellations reference an existing event ID.
ICS imports preserve UID for future updates, and reject unsupported recurrence/all-day cases.

## Reminder policy
Default one minute before start (configurable 1–1440 minutes).
If explicit preparation exists, a preparation reminder is considered at 18:00 the day before.
Only future reminders are scheduled; preparation/action spacing is at least 30 minutes.
Quiet hours, if enabled, move reminders earlier rather than after the event.
At most three delivered reminders per event, including snoozes.
Restart catch-up allows 15 minutes of lateness only while the event is still in the future.
The policy is deterministic; it does not claim AI-generated travel estimates.

## Storage and privacy
SQLite uses WAL and transactions. Sources, pending decisions and trigger status persist.
The model endpoint must be HTTP loopback. Proxy forwarding is disabled for requests.
Model files and all personal data are git-ignored.
No remote data connectors are configured. The user explicitly selects imports or adds files to inbox.
Database encryption, OS wake scheduling and multi-device delivery are not implemented.

## Modes and hardware
Real and demo modes use separate databases. Demo time advances the same scheduler.
Ollama and optional Hailo backends implement the same proposal contract, but feature support
and output accuracy must be validated separately. Hailo is not claimed to be tested.
