"""Manual TinyWorld acceptance checklist.

Run offline tests with:
    python3 -m pytest -q

Run the live app from a normal networked shell with:
    ./start.sh
Then open http://localhost:7860 and use the checklist below.
"""


CHECKS = [
    ("A1", "Marta, go to the clinic", "Only Marta walks to the clinic/nurse building; daily log updates."),
    ("A2", "the power goes out across the block", "All active-world characters react with structured decisions."),
    ("A3", "wait about one minute", "Clock advances; schedules move people; needs and daily logs change."),
    ("A4", "tell Jay to go home and rest", "Only Jay heads to his home and acknowledges the instruction."),
    ("A5", "record mic -> Transcribe -> THROW", "Modal Whisper transcribes, then the event runs."),
    ("A6", "switch to Riverside Campus", "Different board, cast, routines, and school-town locations appear."),
    ("A7", "stop network/Modal and THROW", "Badge turns red and no canned mock line is shown as real output."),
]


if __name__ == "__main__":
    print("TinyWorld acceptance checklist")
    print("Run: python3 -m pytest -q")
    print("Live: ./start.sh -> http://localhost:7860")
    for code, action, expected in CHECKS:
        print(f"{code}: {action} -> {expected}")
