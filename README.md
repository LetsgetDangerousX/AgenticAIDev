# Layered Agentic AI Workflows for Human-Centric Software Development

A user study system that tests whether adding planning and review agents to an LLM coding workflow helps people catch bad AI-generated code, and whether a 3D view of the agents' work changes how much they trust it.

Built for CS 567 (3D User Interfaces) with Dr. Francisco Ortega at Colorado State University, Fall 2026, by Amber Ferrell and Chris Mills. The IRB protocol has been submitted.

## What it does

- A Python multi-agent system on the OpenAI API with Planner, Programmer, and Reviewer agents. Agent outputs are cached, so every participant sees the exact same responses and runs are reproducible.
- Each agent output is scored against hidden tests, and some trials contain seeded failures, so the study can measure whether participants accept code that is actually wrong.
- Participants review the agents' work on a 2D Streamlit app and in a WebXR view on a Meta Quest headset, where the repository, prompts, agent feedback, and code diffs are panels in a 3D room.
- Every decision is logged with correctness, trust and confidence ratings, decision time, and which sections were viewed, then exported for analysis. NASA-TLX measures workload.

## Study design

A 3×2 within-subjects design: three agent workflows crossed with two displays (2D vs. XR). Twelve participants each complete six trials, three per display, with trial order counterbalanced and one seeded-failure trial in each part.

## Team

- **Amber Ferrell:** built the 2D Streamlit participant app, the WebXR participant interface and VR room, the session flow that runs a participant across both devices, hidden-test scoring, the OpenAI provider, and the decision-metrics export. Set up the repository and project workflow.
- **Chris Mills:** built the initial architecture and baseline, the seeded-failure trials, NASA-TLX for both displays, and remote hosting for participants.

## Tech stack

Python, OpenAI API, Streamlit, WebXR, Three.js, JavaScript, unittest

## Running the prototype

Running participant sessions (remote through public links, or in person)? See HOSTING.md.

All commands run from the repository root with Python 3.10+.

    pip install -r requirements.txt

1. Generate the agent outputs for every task and workflow (18 trials). This works offline
   with the demo fixtures; each trial is scored against hidden tests (researcher-only).

    python -m src.backend.main generate --all --provider demo

   With OPENAI_API_KEY in .env (copy .env.example), use --provider openai instead.

2. Start both apps on the laptop (two terminals):

    python -m src.backend.main serve --https      # VR page for the Oculus (prints its address)
    streamlit run src/frontend/app_2d.py           # laptop app: http://localhost:8501

3. Run a participant (IDs p01 to p12). Each participant does 3 trials on the laptop and
   3 in the headset, switching device once. Odd IDs start on the laptop, even IDs start
   in VR. Across 12 participants every workflow, display and task is balanced, and each
   participant gets one seeded-bug trial in each part.

   Before the participant arrives, set up the headset (see Oculus setup) on the VR page
   with their ID. Then enter the same ID in the Streamlit sidebar. Both screens move on
   by themselves: the headset says when it is the participant's turn in VR, and the
   laptop continues once the VR part is done.

   Every decision (with trust/confidence ratings, decision time, which sections were
   viewed when, and whether it was correct) is appended to runtime/decisions.jsonl.
   To rerun a participant, use a new ID or remove their lines from that file.

Oculus setup (Quest 1/2/3/Pro)

VR in a browser only works on https:// pages, so the laptop serves the VR page over
HTTPS on your Wi-Fi. No cable or developer mode needed.

1. Put the laptop and the Oculus on the same Wi-Fi network. Campus Wi-Fi often blocks
   devices from talking to each other; if the headset cannot load the page, use a phone
   hotspot for both.
2. On the laptop run:  python -m src.backend.main serve --https
   It prints an address like https://192.168.1.23:8000. On Windows, if a firewall
   prompt appears, allow Python on private networks.
3. In the headset, open the Browser app (from the app library) and type that address.
4. The first time, it warns "Your connection is not private". Choose Advanced, then
   Proceed. This is expected: the certificate was made by your own laptop.
5. Enter the participant ID and press Start VR session. The headset waits until it is
   the participant's turn, then shows the trial.
6. The participant presses the big blue Enter VR button.

Controls in VR: trigger = click. Grip (hold) = grab and move a panel; while holding,
the thumbstick pushes it away or pulls it closer. Left thumbstick = walk. Right thumbstick
= scroll the panel you point at (up/down) or turn (left/right). Bring a held panel near a
wall and a blue outline shows where it will snap; let go to stick it there. "Reset layout"
puts everything back.

The VR room is a modern loft with a glass wall overlooking the sea at golden hour, built in
src/frontend/web/room.js. The sun position, exposure and all colors are in the THEME block
at the top of that file. Panels snap onto the left, right and back walls.

Alternative with a USB cable (needs developer mode and adb): run the server without
--https, then  adb reverse tcp:8000 tcp:8000  and open http://localhost:8000.

Remote participants (participant edition)

Participants who have their own Quest can run the study at home. They get a copy of the
app with the exact cached agent outputs but no hidden tests, reference solutions, demo
fixtures, tests or scores, and they email back their decisions.jsonl.

1. On the researcher laptop, after the caches are generated (the same ones used in person):

    python -m src.backend.main export-participant
       -> dist/crash-override-participant.zip   (send this to the participant)

   The participant follows README.md inside the zip (PARTICIPANT_SETUP.md here).
   Re-export only if you regenerate caches; participants must all use the same zip.

2. When their file arrives, save it (for example as runtime/remote/p03.jsonl) and run:

    python -m src.backend.main merge runtime/remote/p03.jsonl --dry-run   # check first
    python -m src.backend.main merge runtime/remote/p03.jsonl

   This appends their decisions to runtime/decisions.jsonl with expected_decision and
   correct filled in from your cache, new trial_ids (theirs kept as remote_trial_id), and
   skips anything already merged. Then run analyze as usual.

Researcher tools

    Streamlit sidebar > Researcher preview: view any trial without recording
    http://localhost:8000/xr.html?participant=p02 on the laptop: VR preview (drag, WASD)
    python -m src.backend.main analyze                            # decisions -> runtime/analysis/*.csv
    python -m src.backend.experiment.schedule --participants 12   # full trial order
    python -m src.backend.main evaluate runtime/cache/response_*.json   # re-score caches
    python -m src.backend.experiment.check_suites                 # validate hidden tests
    python -m unittest discover -s tests -t .                     # system tests

Participant-facing text (study intro, program description, questions) is in
experiment/participant_context.json. experiment/hidden_tests, reference_solutions and
demo_fixtures are researcher-only: never show them to agents or participants.
