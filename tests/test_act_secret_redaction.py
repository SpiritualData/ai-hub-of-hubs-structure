"""Secret-value redaction: key shapes are replaced, references and ordinary code are left alone, hostile input is fast."""
import time

import pytest

from hubofhubs.act.secret_redaction import redact


def fake_key(prefix: str, body: str) -> str:
    """A key-shaped value assembled at runtime so no literal secret shape sits in the repo."""
    return prefix + body


@pytest.mark.parametrize("raw", [
    fake_key("AKIA", "ABCDEFGHIJKLMNOP"),
    fake_key("ghp_", "a" * 36),
    "Bearer " + "abcdefghijklmnopqrstuvwxyz0123",
    "password = " + "Abcdefghijklmnop1234567890",
])
def test_redact_covers_common_key_shapes(raw):
    out = redact(f"line {raw} end")
    assert "[redacted]" in out
    assert "abcdefghijklmnopqrstuvwx" not in out and "Abcdefghijklmnop1234567890" not in out


def test_redact_leaves_ordinary_code_alone():
    code = "token = request.headers.get('x')  # password reset flow"
    assert redact(code) == code


def realistic_samples():
    return {
        "CLERK_SECRET_KEY=" + fake_key("sk_li", "ve_abcdefghijklmnop1234567"): "abcdefghijklmnop1234567",
        "export STRIPE_API_KEY='" + fake_key("rk_li", "ve_ABCDEFGHIJKL1234567") + "'": "ABCDEFGHIJKL1234567",
        "FOO_API_KEY=" + fake_key("Zx9", "Qw8Er7Ty6Ui5Op4As3Df2"): "Zx9Qw8Er7Ty6Ui5Op4As3Df2",
        "DB_PASSWORD: correct-horse-battery": "correct-horse-battery",
        '"client_token": "' + fake_key("tok", "enValue1234567890") + '"': "tokenValue1234567890",
        "mongodb+srv://admin:" + fake_key("S3cr", "etPassw0rd") + "@cluster.example.net/db": "S3cretPassw0rd",
        "postgres://user:" + fake_key("p4ss", "word99") + "@db.internal:5432/x": "p4ssword99",
        "redis://:nouser@host": None,
        "mongosh -u admin -p '" + fake_key("Hunter2", "Hunter2") + "' --port 27017": "Hunter2Hunter2",
        "tool --password " + fake_key("swordf", "ish1234"): "swordfish1234",
        "tool --token=" + fake_key("abc", "def1234567"): "abcdef1234567",
        "whsec value " + fake_key("whsec_", "abcdefghijklmnopqrstuv"): "abcdefghijklmnopqrstuv",
        "mail key " + fake_key("re_", "Ab12Cd34_EfGh56Ij78Kl90MnOp"): "Ab12Cd34_EfGh56Ij78Kl90MnOp",
        "voyage " + fake_key("pa-", "Abc123Def456Ghi789Jkl012Mno345Pqr"): "Abc123Def456Ghi789Jkl012Mno345Pqr",
        "anthropic " + fake_key("sk-", "ant-api03-ABCDEFGHIJKLMNOPQRSTUVWX"): "ABCDEFGHIJKLMNOPQRSTUVWX",
        "google " + fake_key("AIza", "SyA1234567890abcdefghijklmnopqrstuv"): "SyA1234567890abcdefghijklmnopqrstuv",
        "gh " + fake_key("github_pat_", "11ABCDEFG0abcdefghijklmnop"): "11ABCDEFG0abcdefghijklmnop",
        "slack " + fake_key("xoxb", "-1234567890-abcdefghij"): "1234567890-abcdefghij",
        "aws " + fake_key("AKIA", "ABCDEFGHIJKLMNOP"): "ABCDEFGHIJKLMNOP",
        "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXk\nAAAA\n-----END OPENSSH PRIVATE KEY-----": "b3BlbnNzaC1rZXk",
    }


@pytest.mark.parametrize("raw,secret", list(realistic_samples().items()))
def test_realistic_secret_shapes_are_redacted(raw, secret):
    out = redact(f"before {raw} after")
    if secret is None:
        return
    assert secret not in out and "[redacted]" in out and out.startswith("before ")


@pytest.mark.parametrize("code", [
    "password = os.getenv('PASSWORD')", "max_tokens = 4096", "token = request.headers.get('x')",
    "sort_key = name", "mkdir -p some/dir && ssh -p 22 host", "x = re_compile_pattern_for_search",
    "password = '$PASSWORD'", "CLERK_SECRET_KEY=${CLERK_SECRET_KEY}", "token: None",
])
def test_redaction_leaves_references_and_ordinary_code_alone(code):
    assert redact(code) == code


def test_redaction_is_fast_on_hostile_input():
    start = time.monotonic()
    for hostile in ("a_" * 200_000, "password=" * 50_000, "-----BEGIN PRIVATE KEY-----" * 20_000, "x" * 400_000):
        redact(hostile)
    assert time.monotonic() - start < 5


def test_a_consumer_key_shape_is_redacted_through_extra_patterns():
    import re
    out = redact("x acme_" + "a" * 20, (re.compile(r"acme_[a-z]{16,}"),))
    assert out == "x [redacted]"
