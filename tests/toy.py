"""Toy seats for the assembly tests: declared into scope hubofhubs for one test, then forgotten."""
import typing
from typing import runtime_checkable

import pytest
from esoi import runtime, solution

SCOPE = "hubofhubs"


@runtime_checkable
class ToyStore(typing.Protocol):
    def put(self, key: str, value: str) -> None: ...
    def get(self, key: str) -> str: ...


@runtime_checkable
class ToyIndex(typing.Protocol):
    def find(self, key: str) -> str: ...


@runtime_checkable
class ToyReport(typing.Protocol):
    def render(self) -> str: ...


class MemoryStore:
    def __init__(self):
        self.rows = {}

    def put(self, key, value):
        self.rows[key] = value

    def get(self, key):
        return self.rows[key]


class StoreIndex:
    def __init__(self, store: ToyStore, prefix: str = ""):
        self.store, self.prefix = store, prefix

    def find(self, key):
        return self.store.get(self.prefix + key)


class IndexReport:
    def __init__(self, index: ToyIndex):
        self.index = index

    def render(self):
        return "report:" + self.index.find("k")


class NeedsMissing:
    def __init__(self, store: ToyStore):
        self.store = store


class LoopA:
    """An index arm that needs a report."""
    def __init__(self, other: ToyReport):
        self.other = other


class LoopB:
    """A report arm that needs an index."""
    def __init__(self, other: ToyIndex):
        self.other = other


class ReportNeedsStore:
    def __init__(self, store: ToyStore):
        self.store = store


class StoreNeedsIndex:
    def __init__(self, index: ToyIndex):
        self.index = index


class IndexNeedsReport:
    def __init__(self, report: ToyReport):
        self.report = report


IDS = ("toy-store", "toy-index", "toy-report")


def declare():
    for sid, protocol in zip(IDS, (ToyStore, ToyIndex, ToyReport)):
        solution(sid, scope=SCOPE)(protocol)


def retire():
    for sid in IDS:
        runtime.forget(sid, SCOPE)


@pytest.fixture
def toys():
    """Declare the toy seats (the hub has no arm for any of them), and forget them afterwards."""
    retire()
    declare()
    yield
    retire()
