"""The arms' environment declarations: complete, matching pyproject, coherent, and the generated files current."""
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from support import ROOT  # noqa: E402

from esoi import requirements as needs  # noqa: E402
from esoi.assemble import AssemblyConfig  # noqa: E402
from esoi.installer import assembly_plan  # noqa: E402

from hubofhubs import assembler, requirements_doc  # noqa: E402

# the distribution that provides an importable module, where the two names differ
DISTRIBUTION_OF = {"google.genai": "google-genai", "qdrant_client": "qdrant-client", "Stemmer": "PyStemmer", "acp": "agent-client-protocol"}


def declared_arms():
    return assembler().closure(AssemblyConfig(), None, (), True)


def test_every_arm_declares_its_requirements():
    missing = [m.label for m in declared_arms() if not hasattr(m.target, "REQUIRES")]
    assert not missing, f"arms without REQUIRES (use () for an arm that needs nothing): {missing}"


def test_every_python_requirement_is_provided_by_the_extra_it_names():
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["optional-dependencies"]
    for member in declared_arms():
        for item in needs.declared(member.target):
            if not isinstance(item, needs.Python):
                continue
            assert item.parsed.name == "hubofhubs" and item.extra in extras, (member.label, item)
            wanted = DISTRIBUTION_OF.get(item.module, item.module).lower().replace("_", "-")
            provided = [re.split(r"[<>=!~\[ ]", spec)[0].lower().replace("_", "-") for spec in extras[item.extra]]
            assert wanted in provided, f"{member.label}: module {item.module} is not provided by extra {item.extra}: {extras[item.extra]}"


def test_every_api_key_is_secret_and_every_api_names_a_date_and_a_link():
    for member in declared_arms():
        for item in needs.declared(member.target):
            if isinstance(item, needs.Api):
                assert item.key is None or item.key.secret, (member.label, item.service)
                assert item.as_of and (item.signup_url or item.docs_url), (member.label, item.service)


def test_the_selected_implementations_resolve_together_offline():
    hub = assembler()
    chosen, _closure = assembly_plan(hub, AssemblyConfig(), {}, (), False, None)
    assert not chosen.adjusted, chosen.conflicts


def test_the_generated_reference_and_env_example_are_current():
    page = (ROOT / "docs" / "reference" / "requirements-by-arm.md").read_text()
    assert requirements_doc.requirements_block() in page, "run python3 scripts/status.py"
    assert (ROOT / ".env.example").read_text() == requirements_doc.env_example(), "run esoi requirements --package hubofhubs --env-template .env.example"
