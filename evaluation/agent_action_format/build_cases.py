"""Rebuild cases.json for Agent Action Format: scripted model replies in each format over a temporary folder, and the effect each must have. Fifteen cases.

The formats are the hub loop's text protocol (``protocol``), the function-call markup a model writes when it forgets the protocol (``function-markup``, a real
defect of a real run), a fenced JSON action (``json-tool-call``) and tool calls in the shape of Claude Code's own tools (``native-tool-calls``: Bash, Read,
Write, Edit, Glob, several calls in one reply, and an edit whose old text is not unique). Each case says what a correct execution leaves: the files, their text
and the number of actions that must have run. No model call: the replies are written, not sampled.

    python3 evaluation/agent_action_format/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
F = "`" * 3


def case(name, fmt, reply, files=None, **expect):
    return {"id": f"agent-action-format-{name}", "format": fmt, "args": {"reply": reply, "files": files or {}}, "expect": expect}


def calls(*items):
    return json.dumps([{"name": n, "input": i} for n, i in items])


def edit_block(path, old, new):
    return f"{path}\n{F}\n<<<<<<< SEARCH\n{old}=======\n{new}>>>>>>> REPLACE\n{F}\n"


def main():
    cases = [
        case("run-one-line", "protocol", "RUN: echo hi > out.txt\nCHECK: test -s out.txt\nREPORT: wrote out.txt", has={"out.txt": "hi"}, ran=2),
        case("run-several-lines", "protocol", "RUN:\n" + F + "bash\nset -e\nmkdir -p d\nfor i in 1 2 3; do echo $i >> d/n.txt; done\n" + F + "\nREPORT: made d/n.txt", has={"d/n.txt": "1\n2\n3"}, ran=1),
        case("edit-block", "protocol", "I fix it.\n" + edit_block("a.py", "x = 1\n", "x = 2\n") + "REPORT: changed", {"a.py": "x = 1\n"}, has={"a.py": "x = 2"}, ran=1),
        case("bold-marker", "protocol", "**RUN:** echo bold > bold.txt\nREPORT: ok", has={"bold.txt": "bold"}, ran=1),
        case("read-a-file", "protocol", "READ: notes.txt\nREPORT: the limit", {"notes.txt": "limit 100\n"}, ran=1),
        case("markup-run", "function-markup", '<function_calls>\n<invoke name="RUN">\n<parameter name="command">echo viaMarkup > m.txt</parameter>\n</invoke>\n</function_calls>\nREPORT: done', has={"m.txt": "viaMarkup"}, ran=1),
        case("markup-bash-name", "function-markup", '<invoke name="Bash"><parameter name="command">echo b > b.txt</parameter></invoke>\nREPORT: made b.txt', has={"b.txt": "b"}, ran=1),
        case("markup-wrapping-protocol", "function-markup", '<invoke name="RUN">\nRUN: echo wrapped > w.txt\n</parameter>\n</invoke>\nREPORT: ok', has={"w.txt": "wrapped"}, ran=1),
        case("json-fence", "json-tool-call", F + 'json\n{"action": "RUN", "command": "echo j > j.txt"}\n' + F + "\nREPORT: made j.txt", has={"j.txt": "j"}, ran=1),
        case("native-bash", "native-tool-calls", calls(("Bash", {"command": "echo nb > nb.txt"})), has={"nb.txt": "nb"}, ran=1),
        case("native-write-and-read", "native-tool-calls", calls(("Write", {"file_path": "w/x.txt", "content": "hello"}), ("Read", {"file_path": "w/x.txt"})), has={"w/x.txt": "hello"}, ran=2),
        case("native-edit", "native-tool-calls", calls(("Edit", {"file_path": "a.py", "old_string": "x = 1", "new_string": "x = 2"})), {"a.py": "x = 1\n"}, has={"a.py": "x = 2"}, ran=1),
        case("native-several-calls", "native-tool-calls", calls(("Bash", {"command": "mkdir -p out"}), ("Write", {"file_path": "out/a.txt", "content": "A"}), ("Bash", {"command": "cat out/a.txt > out/b.txt"})), has={"out/b.txt": "A"}, ran=3),
        case("native-edit-not-unique-is-refused", "native-tool-calls", calls(("Edit", {"file_path": "a.py", "old_string": "x", "new_string": "y"})), {"a.py": "x\nx\n"}, has={"a.py": "x\nx"}, ran=1, failed=1),
        case("native-path-outside-is-refused", "native-tool-calls", calls(("Write", {"file_path": "../escape.txt", "content": "no"})), absent=["../escape.txt"], ran=1, failed=1),
    ]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
