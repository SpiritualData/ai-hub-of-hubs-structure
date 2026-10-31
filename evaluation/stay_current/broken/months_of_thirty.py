"""BASELINE: the naive age. Months of thirty days from the year and month only, and no handling of a date that does not parse. Zero model calls."""


def build(meter):
    def run(kind, args):
        if kind == "combine":
            return {"coverage": 1.0, "fresh_share": 1.0}
        year, month, day = (int(p) for p in args["iso"].split("-"))
        ty, tm, td = (int(p) for p in args["today"].split("-"))
        return (ty - year) * 360 + (tm - month) * 30 + (td - day)
    return run
