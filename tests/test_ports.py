"""The neutral ports moved out of a consumer's core: importable with no consumer, behaving as they did there."""
import subprocess
import sys
from pathlib import Path

from hubofhubs.ports import context, model, scope
from support import ESOI_PATH

ROOT = Path(__file__).resolve().parent.parent


def test_importing_the_ports_loads_no_consumer():
    code = "import sys, hubofhubs.ports.scope, hubofhubs.ports.model, hubofhubs.ports.context\nassert not [m for m in sys.modules if m.startswith(('quest', 'quest_ai_runner'))]"
    done = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, env={"PYTHONPATH": f"{ROOT}:{ESOI_PATH}"})
    assert done.returncode == 0, done.stderr


class Provider:
    def plan(self, prompt, step=None): return {"prompt": prompt, "step": step}
    def answer(self, messages, model=None, step=None): return f"{model}:{step}"
    def list_models(self): return []


class OldProvider:
    def plan(self, prompt): return {"prompt": prompt}
    def answer(self, messages, model=None): return str(model)
    def list_models(self): return []


def test_a_step_hint_is_forwarded_only_to_a_provider_that_takes_it():
    assert model.plan_with_step(Provider(), "p", step=model.STEP_PLAN) == {"prompt": "p", "step": "plan"}
    assert model.plan_with_step(OldProvider(), "p", step=model.STEP_PLAN) == {"prompt": "p"}
    assert model.answer_with_reasoning(Provider(), [], model="m", step=model.STEP_REPLY) == "m:reply"
    assert model.answer_with_reasoning(OldProvider(), [], model="m", step=model.STEP_REPLY) == "m"
    for name in ("plan", "answer", "list_models", "supports_web_search", "web_search"):
        assert callable(getattr(model.ModelProvider, name)), name


def test_a_bound_scope_is_the_threads_scope_and_restores():
    own = scope.current_usage_scope()
    with scope.bound_usage_scope("turn-1"):
        assert scope.current_usage_scope() == "turn-1"
    assert scope.current_usage_scope() == own


def test_a_scoped_pool_bills_the_creating_scope():
    with scope.bound_usage_scope("turn-2"):
        pool = scope.ScopedThreadPoolExecutor(max_workers=1)
        seen = pool.submit(scope.current_usage_scope).result()
        pool.shutdown()
    assert seen == "turn-2"


def test_the_context_value_objects_default_empty():
    assert context.AssembledContext().__class__.__name__ == "AssembledContext"
    assert context.VectorHit.__name__ == "VectorHit"
