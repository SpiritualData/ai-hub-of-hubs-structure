"""BASELINE: the naive adapter. The tier is passed on as the model id, no mapping, no default, no system prompt, and a failure is swallowed. Zero model calls."""


def build(meter):
    def run(kind, args):
        tier = (args.get("tier") or [""])[0]
        reply = "" if args.get("fail") else args.get("reply", "ok")
        return [reply, [[[{"role": "user", "content": args["prompt"]}], tier, None]]]
    return run
