"""Smoke test: every third-party package the web app imports at *runtime*
must be installable from ``requirements.txt``.

Why this test exists
--------------------
Several modules (``chatgpt_format``, ``readdata`` for pandas, etc.) use a
*lazy* ``import`` inside a function body so that the rest of the app keeps
working even when the dependency is missing. The parity tests in
``tests/parity/_runner.py`` then monkey-patch some of those modules into
``sys.modules`` (e.g. it injects a fake ``openai``) so the prompt-shape
tests can run without a real install.

That is great for unit-testing the prompt, but it also means a missing
dependency in ``requirements.txt`` will pass CI and only blow up in
production with a flash message like
``ChatGPT formatting failed: No module named 'openai'`` — exactly what
happened on Render after the parity-feature rollout.

This test imports every runtime third-party package directly, with no
stubs, so a missing entry in ``requirements.txt`` fails CI.
"""

from __future__ import annotations

import importlib

import pytest


RUNTIME_PACKAGES = [
    "flask",        # web framework
    "openai",       # ChatGPT citation parsing
    "openpyxl",     # xlsx export
    "pandas",       # readdata.py uses it lazily
]


@pytest.mark.parametrize("pkg", RUNTIME_PACKAGES)
def test_runtime_package_is_installable(pkg):
    """Importing each runtime package must succeed in this environment.

    If this fails for ``openai`` (or any other entry above), add it to
    ``requirements.txt`` so Render / your prod host installs it.
    """
    try:
        importlib.import_module(pkg)
    except ModuleNotFoundError as exc:
        pytest.fail(
            f"Runtime dependency {pkg!r} is not installed in this "
            f"environment ({exc}). Add it to requirements.txt so the "
            f"deployment installs it; otherwise users will hit a "
            f"ModuleNotFoundError when the relevant feature runs."
        )


def test_chatgpt_format_lazy_import_path_works():
    """The lazy ``import openai`` inside ``format_citations_with_chatgpt``
    must reach a real ``openai`` package — not the parity-runner stub."""
    from modules.chatgpt_format import format_citations_with_chatgpt  # noqa: F401

    openai_mod = importlib.import_module("openai")
    assert hasattr(openai_mod, "OpenAI"), (
        "openai package is installed but does not expose OpenAI client. "
        "Pin to openai>=1.0 in requirements.txt."
    )
