# CommStat Pre-Release Code Review

## Context

CommStat is feature-complete from the owner's perspective — all planned options
and features are in place. Before declaring the app done, the owner asked for a
holistic review across the codebase looking for: real bugs, optimization
opportunities, legacy code, duplication, best-practice issues, and "things I
didn't mention."

This document is **report-only**. No code changes are proposed for this turn —
the owner will triage findings and request implementations in separate sessions.

Codebase shape, for context:
- 25 Python files, ~24k LOC total
- `little_gucci.py` is the monolith (6,284 LOC) — `MainWindow` + 7 helper classes
- `commstat.py` is a thin launcher that runs update logic, then spawns the main app
- PyQt5 GUI, sqlite (`traffic.db3`) persistence, QTcpSocket to JS8Call
- Mixed concurrency: 3 `QThread` subclasses (qrz_lookup), 5 `threading.Thread`
  daemons (alert/group_message/statrep/qrz_settings/tcp_test_tool), QTimers,
  Qt signal/slot

Findings below are grouped into three tiers by risk and effort. Severity is
tagged per finding so individual items can be promoted/demoted out of their tier.

---

## Tier 1 — Real Bug Risks (recommended before release)

### 1.1 [HIGH] Linux-segfault crash pattern still present in two files
**Files:** `alert.py:86-94`, `statrep.py:123-132`

Both define `make_uppercase(field)` with the same re-entrant pattern that just
crashed a Linux user in `js8_direct_message.py` — calling `field.setText()` from
inside the line edit's own `textChanged` slot:

```python
def to_upper(text):
    if text != text.upper():
        pos = field.cursorPosition()
        field.blockSignals(True)
        field.setText(text.upper())
        field.blockSignals(False)
        field.setCursorPosition(pos)
field.textChanged.connect(to_upper)
```

This is the exact pattern that segfaulted on Linux when the user typed a target
callsign. It hasn't bit `alert.py` / `statrep.py` users yet but the failure
mode is identical and platform-dependent.

Need to review the code in `js8_direct_message.py:74-86` as it was recently changed.

### 1.2 [HIGH] TCP client signals never disconnected when dialogs close
**Files:** `alert.py:139-142` (and likely `js8sms.py`, `js8mail.py`,
`group_message.py:340-344`)

Dialogs call `client.frequency_received.connect(...)` (and friends) inside
`_on_rig_changed`, but no `closeEvent` override disconnects them. After the
dialog is destroyed, the TCP client still holds references to Python callbacks
that target deleted `QObject`s. On the next frequency update, Qt will dispatch
into a deleted widget — silent leak or hard crash.

`js8_direct_message.py:393-399` does an *opportunistic* disconnect at the top
of `_on_rig_changed` (good), but still doesn't disconnect on dialog close.

**Recommended fix:** Add a `closeEvent` to every dialog that connects to TCP
client signals; iterate the same signal list disconnecting each in a
try/except. Pattern already exists in `qrz_lookup.py:1950-1959`.

### 1.3 [MEDIUM] Manual `sqlite3.connect` calls bypass context managers
**Files:** `little_gucci.py:2837, 2920, 3004, 3166, 3375, 3449`, plus
`alert.py:536-548`, `group_message.py:493-505`

Most of the codebase uses `with sqlite3.connect(DATABASE_FILE, timeout=10) as
conn:` — but these six spots in `little_gucci.py` and the submit paths in
`alert.py` / `group_message.py` open connections without `with`. If the
function raises mid-transaction, the connection is leaked and the row may not
be committed/rolled back deterministically.

**Recommended fix:** Wrap each in `with sqlite3.connect(...) as conn:`.
Mechanical change; no behavior change on the happy path.

### 1.4 [MEDIUM] `urlopen` not guaranteed to close on exception
**File:** `qrz_lookup.py:1645-1647`

```python
try:
    urllib.request.urlopen(url, timeout=10).close()
except Exception:
    pass
```

If `urlopen` raises after the socket is created but before `.close()`, the
socket leaks. The bare `except: pass` also hides legitimate connectivity
errors that might be worth logging.

**Recommended fix:**
```python
try:
    with urllib.request.urlopen(url, timeout=10):
        pass
except Exception as e:
    print(f"[QRZ] connectivity check failed: {e}")
```

### 1.5 [MEDIUM] Missing/duplicate signal-disconnect risk in `_on_rig_changed`
**File:** `js8_direct_message.py:393-409`

The opportunistic disconnect loop only handles `frequency_received`. Other
dialogs connect `callsign_received` / `grid_received` / `speed_received` in
similar handlers — if a user changes rigs twice without closing the dialog,
the slot fires N times per event. Verify which dialogs do this and audit.

**Recommended fix:** Either disconnect *all* relevant signals at the top of
each `_on_rig_changed`, or (better) only connect once in `__init__` and route
to the currently-selected rig in the slot.

---

## Tier 2 — Maintainability / Polish

### 2.1 [LOW] Leftover dev flag and commented test values
**File:** `constants.py:20, 72, 78-79`

- `DEV_RELOAD_DIALOGS = False` — dev-only auto-reload flag. Either document
  its purpose with a clear comment or delete it.
- Lines 72, 78-79: commented `#'program_background': '#DDDDDD'` and
  `#'title_bar_background': '#FFFF00'` test overrides. Delete.

### 2.2 [MEDIUM] Hardcoded hex in `ui_helpers.py` defeats the constants module
**File:** `ui_helpers.py:49, 50, 73, 91-92`, `brevity.py:1130, 1238, 1243,
1248, 1253, 1258`

Examples:
- `ui_helpers.py:49` uses `"#28a745"` instead of `COLOR_BTN_GREEN`
- `ui_helpers.py:50` uses `"#6c757d"` (no constant exists — add `COLOR_BTN_GRAY`)
- `brevity.py` hardcodes `#28a745`, `#dc3545`, `#17a2b8`, `#007bff` directly

`constants.py` already exports `COLOR_BTN_RED/GREEN/BLUE/CYAN`. Replace inline
hex with the constants so a future palette change is one edit.

### 2.3 [MEDIUM] Linux users without Roboto/Kode Mono get layout drift
**Files:** every stylesheet that names `'Roboto'`, `'Roboto Slab'`, `'Kode Mono'`
without a fallback (50+ occurrences across all dialogs)

If the fonts aren't installed system-wide on a Linux box, Qt silently falls
back to the system default — usually with different metrics, breaking the
careful fixed-size layouts. `commstat.py` does load the bundled `.ttf` files
at startup, which mitigates this when those files are present — but if the
load fails (path issue, permissions), there's no graceful fallback.

**Recommended fix:** Use CSS-style font-family chains in every stylesheet:
`font-family:'Roboto', 'DejaVu Sans', sans-serif;` and
`font-family:'Kode Mono', 'DejaVu Sans Mono', monospace;`. Define
`FONT_ROBOTO_STACK` / `FONT_MONO_STACK` in `constants.py` and use those
everywhere.

### 2.4 [MEDIUM] Dialog scaffolding repeated in every dialog
**Files:** `js8_direct_message.py:92-103`, `js8sms.py:65-76`,
`js8mail.py:438-440`, `filter.py:41-52`, `alert.py`, `statrep.py`, etc.

Every dialog repeats:
```python
self.setWindowTitle("...")
self.setFixedSize(W, H)
self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint |
                    Qt.WindowTitleHint | Qt.WindowCloseButtonHint |
                    Qt.WindowStaysOnTopHint)
if os.path.exists("radiation-32.png"):
    self.setWindowIcon(QtGui.QIcon("radiation-32.png"))
```

**Recommended fix:** Add `apply_standard_dialog_chrome(dialog, title, w, h)`
to `ui_helpers.py`. One call per dialog.

### 2.5 [LOW] Magic timing numbers duplicated in code
**Files:** `little_gucci.py:2011, 4421` (both `15000`),
`statrep.py:497-498` (`100`, `200`), `group_message.py:351` (`100`),
`qrz_lookup.py:1188` (`200`)

Heartbeat interval `15000` appears in two places. Should be
`HEARTBEAT_INTERVAL_MS` in `constants.py`. Same for the `100`/`200`ms
post-rig-select delays — name them `GRID_FETCH_DELAY_MS` etc.

### 2.6 [LOW] `commdata.ui` Qt Designer file is not loaded anywhere
**File:** `commdata.ui` (repo root)

If grep confirms it's not referenced (the agents didn't find a `uic.loadUi`
call), it's a vestigial artifact. Either delete it or move it to a
`design/` folder with a README explaining its purpose.

---

## Tier 3 — Optional / Architectural

### 3.1 sqlite usage scattered across 14 files
14 files each call `sqlite3.connect(DATABASE_FILE, timeout=10)` with their own
error handling style. A thin `db_utils.py` with:
```python
@contextmanager
def db_connection():
    conn = sqlite3.connect(DATABASE_FILE, timeout=10)
    try:
        yield conn
    finally:
        conn.close()
```
…would let every caller drop the `timeout=10` literal and unify error logging.
Low value if everything already uses `with`; medium value if Tier 1.3 doesn't
get done.

### 3.2 No index on `contacts.freq`
**Files:** `js8_direct_message.py:462-467, 493-499`,
`group_message.py` (similar queries)

Both dialogs do `SELECT ... WHERE freq = ? ORDER BY target_snr DESC` on every
keystroke / target change. On a busy roster (thousands of rows), this is a
full scan. Add a composite index on `(freq, target_cs)` in the schema
template and in a one-shot migration at startup.

### 3.3 `print()` as a logger (232 call sites)
The mix of `[QRZ]`, `[Rich]`, `[JS8SMS]`, etc. prefixes is effectively a
home-rolled logger. Stdlib `logging` with per-module loggers and a single
formatter would give: timestamps, level filtering, an opt-in log file. Big
change touching many files — only worth it if you ever want users to send
you a log file.

### 3.4 Schema integrity check at startup
`commstat.py:84` warns if `traffic.db3.template` is missing but then launches
anyway. If the user has an old `traffic.db3` missing a table (e.g.,
`js8_connectors` from a recent version), the first insert crashes with a
cryptic `sqlite3.OperationalError: no such table`. Consider a startup
"required tables present?" check that recreates missing tables from the
template.

### 3.5 Bare `except Exception:` / silent swallowing
**Files:** `qrz_lookup.py:1646-1647`, `little_gucci.py:2856-2857`,
`statrep.py:151`, `tcp_test_tool.py:124`

Several places catch broadly and `pass`. At minimum, log the exception so a
support session can grep for it. Already partially covered under 1.4.

### 3.6 Monolithic `MainWindow` in `little_gucci.py` (6,284 LOC)
Not a bug, but a maintainability cliff: the class mixes TCP dispatch, message
parsing, alert/statrep rendering, map generation, RSS feeds, and config UI.
Splitting into a few service objects (e.g., `MessageRouter`, `RssService`)
that the MainWindow composes would help future changes. High effort,
high churn — only worth it if you anticipate continued development.

---

## Quick-Triage Summary

If you want a minimal, low-risk pre-release pass, just **1.1 and 1.2** address
the only two findings that can actually crash the app. Everything else is
quality-of-life.

| # | Severity | Effort | Crash risk? |
|---|----------|--------|-------------|
| 1.1 Validator port | HIGH | XS | Yes (Linux) |
| 1.2 closeEvent signal cleanup | HIGH | S | Yes (rare) |
| 1.3 sqlite `with` wrapping | MEDIUM | S | No |
| 1.4 urlopen leak | MEDIUM | XS | No |
| 1.5 rig-change signal audit | MEDIUM | M | Sometimes |
| 2.1 dev flag / commented code | LOW | XS | No |
| 2.2 hardcoded hex | MEDIUM | S | No |
| 2.3 font fallbacks | MEDIUM | S | No (layout drift) |
| 2.4 dialog chrome helper | MEDIUM | M | No |
| 2.5 magic timing numbers | LOW | XS | No |
| 2.6 unused `commdata.ui` | LOW | XS | No |
| 3.1 db_utils helper | LOW | M | No |
| 3.2 contacts index | LOW | XS | No (perf) |
| 3.3 logging migration | LOW | L | No |
| 3.4 schema integrity check | MEDIUM | S | Sometimes |
| 3.5 bare excepts | LOW | S | No |
| 3.6 little_gucci split | LOW | XL | No |

---

## Critical files referenced

- `/Users/mochoa/Github/CommStat/alert.py:86-94` — make_uppercase, same crash pattern
- `/Users/mochoa/Github/CommStat/statrep.py:123-132` — make_uppercase, same crash pattern
- `/Users/mochoa/Github/CommStat/js8_direct_message.py:74-86` — reference fix to port
- `/Users/mochoa/Github/CommStat/qrz_lookup.py:1645-1647, 1950-1959` — urlopen leak & disconnect pattern to copy
- `/Users/mochoa/Github/CommStat/little_gucci.py:2837, 2920, 3004, 3166, 3375, 3449` — manual sqlite connects
- `/Users/mochoa/Github/CommStat/constants.py:20, 72, 78-79` — dev flag + commented colors
- `/Users/mochoa/Github/CommStat/ui_helpers.py:49, 50, 73` — hardcoded hex
- `/Users/mochoa/Github/CommStat/commdata.ui` — verify dead resource

## Verification (when items are implemented later)

These are notes for the implementation sessions that follow, not actions for now:

- **1.1:** Type a lowercase callsign into the From/To fields in `alert.py` and
  `statrep.py` dialogs on Linux. Should uppercase live, no crash. Repeat with
  paste of mixed-case text.
- **1.2:** Open a dialog with a connected rig, change rigs, close the dialog,
  then trigger another frequency update on the TCP client. No "wrapped C++
  object has been deleted" warning in stderr.
- **1.3:** Run any code path that hits the affected sqlite calls; the
  behaviour shouldn't change. Smoke-test by running `commstat.py` and
  exercising each affected dialog.
- **2.3:** Uninstall Roboto fonts on a Linux test box (or temporarily rename
  the bundled `.ttf` files) and confirm the UI is legible — not necessarily
  pixel-perfect, just no overlapping/clipped text.
- **3.2:** `EXPLAIN QUERY PLAN` on the relay-lookup queries should show
  `SEARCH ... USING INDEX` instead of `SCAN`.
