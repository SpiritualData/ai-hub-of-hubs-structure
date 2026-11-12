"""``python -m hubofhubs.the_consciousness.ai_session_experience.acp_agent --demo``: the scripted demo harness (no model) served over stdio, for trying an ACP client or a test.
The real command is ``ahohs acp``."""
import argparse
import tempfile
from pathlib import Path

from hubofhubs.the_consciousness.ai_session_experience.acp_agent.server import AcpUnavailable, HubAgent, serve
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import demo_harness


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m hubofhubs.the_consciousness.ai_session_experience.acp_agent")
    parser.add_argument("--demo", action="store_true", required=True, help="serve the scripted demo harness (read, a change, a helper, a risky deploy that waits, the report)")
    parser.add_argument("--pause", type=float, default=0.3, help="seconds the demo pauses between steps")
    args = parser.parse_args()

    def build(folder: str):
        work = folder if Path(folder).is_dir() else tempfile.mkdtemp(prefix="acp-demo-")
        return demo_harness("stream", work, args.pause)
    try:
        serve(HubAgent(build, steering=True, acting_for="the demo person"))
    except AcpUnavailable as error:
        print(error, file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
