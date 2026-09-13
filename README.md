# THREAD

**Know what changed. Know what needs you.**

A working local prototype for a fictional caregiver handoff. THREAD connects an exact source quotation to a transport task and its acknowledgement. When a claimed replacement changes the appointment, the old review becomes stale and stays visible in history.

**For judges:** [Run it](#run-it) · [Try the demonstration](#try-the-demonstration) · [Five judging criteria](#five-judging-criteria) · [Evidence and limitations](#evidence-and-limitations)

## Run it

Python 3.10 or later; no third-party Python packages, API key or build step required. Current local verification used Python 3.14 and Node 26.

```bash
git clone https://github.com/dumbthing999-ui/thread-caregiver.git
cd thread-caregiver
python3 run_app.py --port 8000
```

Open **http://127.0.0.1:8000/**. The web page is served by Python; opening the HTML file directly will not provide its API.

Optional local SQLite persistence:

```bash
python3 run_app.py --port 8000 --db thread.db
```

The default is in-memory storage. Database files are excluded from Git. Keep the server bound to localhost: actor identities in this prototype are simulated, not production authentication. No hosted deployment is claimed.

## Try the demonstration

1. **Open fictional example.** Read the original source. The appointment quotation is “Follow-up appointment: Thursday at 10:00.” The source viewer shows the literal document and, after review, the service's exact character span.
2. **Review, then coordinate.** Choose “I’ve reviewed this source,” then “I’ll arrange transport.” Acknowledge the wording as a separate action. Neither action marks the ride completed.
3. **Compare the new note.** The update contains Friday at 14:00. Adding it does not record a replacement. Inspect both notes and explicitly confirm the claimed replacement relationship.
4. **See what needs attention.** The old task and acknowledgement become stale. Review and acknowledge the update; inspect history to see the original event retained.
5. **Check the evidence.** Expand “Explore the demo’s evidence.” Try an old acknowledgement: the service must return `409 STALE_REVISION_ERROR` without adding an event. Retry the original accepted acknowledgement: its ID and event count must remain unchanged.
6. **Try disagreement.** Open the separate conflicting-note example. Both sources and a neutral clarification question stay visible; the interface does not choose either appointment. Return to the original handoff without losing it.
7. **Export or reset.** JSON export retains source/version and history information with simulation labels. Reset affects only the current example. Downloaded exports are not removed by reset.

This is a manual, real-service demonstration. No auto-play success, live AI, clinical authentication or medical advice is presented. Refreshing the page starts a fresh UI view; use export to retain a copy.

## Five judging criteria

| Criterion | What to inspect in this project | What remains to improve or validate |
| --- | --- | --- |
| **Idea & Innovation** | The visible chain: changed source → stale transport review → explicit re-review. [Competitor research](docs/day02/competitor-analysis.md) explains overlap with existing products. | Establish whether this narrow workflow is meaningfully useful beyond versioned documents and shared checklists. No first-ever claim. |
| **Implementation** | Exact source spans, separate ownership and acknowledgement, explicit replacement, stale/duplicate request checks, history and SQLite option. See [domain logic](app/domain.py) and [HTTP tests](tests/test_server_api.py). | Production authentication, complete atomic concurrency guarantees, broader input validation and independent security review remain unfinished. |
| **Health Impact & Rigor** | A bounded fictional example for an adult family caregiver arranging transport. Missing/conflicting wording stays visibly unresolved; medication is source text only. | Consenting caregiver walkthroughs and a fair plain-document baseline are still needed. No patient outcomes, user-study results or clinical benefit measured. |
| **Design & Usability** | One primary next action, four visible stages, plain-language states, side-by-side changes, source dialog, persistent activity history, error/offline feedback and responsive layout rules. | Keyboard, screen-reader and mobile usability need actual browser/user observation. The controller test does not establish accessibility conformance. |
| **Presentation** | Follow the steps above, show the old/new quote and the real rejection response, then inspect the retained event. “About this prototype” separates working behavior from unproven claims. | Record the running app and add an accessible captioned video after reviewing the live UI. No demo video or hosted site is claimed here. |

## Evidence and limitations

Verified locally for this revision:

- **32 Python tests pass** across current domain, storage, rehearsal, HTTP and contract examples.
- **UI-controller integration passes** against an isolated real HTTP service: source inspection, separate assignment/acknowledgement, explicit replacement/cancellation, stale rejection, exact retry, updated review, separate conflict case, offline recovery, safe text and scoped reset.
- **JavaScript syntax check passes.**

Reproduce:

```bash
make check
# or run each check explicitly:
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_*.py"
node --check app/ui.js
node tests/test_ui_flow.js
```

`make run` starts the local demo on port 8000. The Makefile is only a convenience; the explicit commands above show exactly what is being run.

Node is optional for running the application; it is required only for the UI-controller test. The controller test uses a minimal DOM adapter and the actual service, **not a real browser**. The connected browser was unavailable during this UI update, so visual rendering, keyboard usability and assistive-technology behavior have not been verified. Test counts describe these tests only, not full contract compliance or production readiness.

Initial invalidation is **whole-document**: unchanged content may also need review. Sources, actor names and scenarios are fictional. An explicit replacement is a claim about a relationship, not authenticated clinical authority. Rehearsal APIs and tests remain in the codebase; the main UI focuses on the transport handoff instead of making practice a prerequisite.

## Where to look

| Path | Purpose |
| --- | --- |
| [app/ui.html](app/ui.html), [ui.css](app/ui.css), [ui.js](app/ui.js) | Guided interface, responsive styling and service-connected actions |
| [app/domain.py](app/domain.py) | Source records, coordination state, replacement and event logic |
| [app/server.py](app/server.py) | Local HTTP API and bundled asset delivery |
| [app/storage.py](app/storage.py) | SQLite adapter |
| [tests/](tests/) | Current executable behavior checks |
| [docs/day03/fixtures/](docs/day03/fixtures/) | Original fictional inputs used by the demo |
| [docs/day02/competitor-analysis.md](docs/day02/competitor-analysis.md) | Sourced positioning and arguments against novelty |
| [AGENTS.md](AGENTS.md) | Current lean development guide |

Historical day documents and experimental spikes remain reference material. The legacy suite in `tests/day04/` intentionally exposes failures in the **old spikes**, not the current application. Its known-failure baseline is not product success and is not the current release check. Some historical documents contain superseded readiness statements and local-only references; use this README and current executable tests for the present scope.

## Next useful work

Validate this flow with consenting adults using fictional cases; compare it with a plain document/checklist; address observed confusion before expanding features. Establish genuine server-side identity and atomic write protection before any public deployment. No real health records, prescribing, dose calculations, administration tracking or clinical validation belong in this demo.

AI coding assistants contributed code, design and testing. Human entrant comprehension and review are not inferred from that assistance. Eligibility and organizer clarification remain pending before registration or submission. No submission or external validation is claimed.
