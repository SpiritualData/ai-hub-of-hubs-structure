"""A stand-in for the one program a plain install needs, the Claude CLI: it answers the way the real one's JSON envelope does, with nothing else faked.

``install(folder)`` writes an executable ``claude`` into ``folder`` and returns the folder; put it alone on the PATH of the run's environment mapping and
(for a process that starts it) of the process. A search prompt gets one JSON object with an answer and one source; any other prompt gets a short reply. Each call is a line of ``claude.calls`` beside the program.
Standard library only."""
import stat
import sys
from pathlib import Path

SCRIPT = '''#!{python}
import json, sys
args = sys.argv[1:]
if "--version" in args:
    print("2.0.0")
elif "--help" in args:
    print("claude --help")
else:
    prompt = sys.stdin.read()
    with open(__file__ + ".calls", "a") as log:      # one line per model call, so a test can say a question made none
        log.write(prompt[:60].replace("\\n", " ") + "\\n")
    if "Search the web for" in prompt:
        reply = json.dumps({{"answer": "Python 3.15 is the current stable release.", "results": [
            {{"title": "Download Python", "url": "https://www.python.org/downloads/", "snippet": "The current stable release.", "date": ""}}]}})
    else:
        reply = "ok"
    print(json.dumps({{"result": reply, "usage": {{"input_tokens": 3, "output_tokens": 2}}, "total_cost_usd": 0.0}}))
'''


def install(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    program = folder / "claude"
    program.write_text(SCRIPT.format(python=sys.executable))
    program.chmod(program.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return folder
