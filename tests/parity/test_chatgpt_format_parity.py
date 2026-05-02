"""
Parity test: ``modules.chatgpt_format.format_citations_with_chatgpt``.

We do NOT call OpenAI. Instead we monkey-patch ``openai.OpenAI`` so the call
is captured. Then we assert that desktop and web build the same prompt
(model, role, content) for the same input. The only intentional divergence
is **how the API key is sourced** (desktop hardcodes a key in source; web
reads ``OPENAI_API_KEY`` from the environment) — both paths must still
produce a working call when a valid key is supplied. The hardcoded key on
the desktop is also flagged in the parity report as a security finding.
"""

from __future__ import annotations


def test_prompt_text_identical(parity):
    desktop, web = parity(
        "chatgpt_format.prompt",
        {"raw_text": "McCarl, B.A. (2024) On Climate. Nature 600, 1-7."},
    )
    assert desktop["capture"] is not None, "desktop did not call openai client"
    assert web["capture"] is not None, "web did not call openai client"

    assert desktop["capture"]["model"] == web["capture"]["model"], (
        f"model differs: desktop={desktop['capture']['model']}, web={web['capture']['model']}"
    )
    # Compare each message (role + content) verbatim.
    d_msgs = desktop["capture"]["messages"]
    w_msgs = web["capture"]["messages"]
    assert len(d_msgs) == len(w_msgs)
    for d, w in zip(d_msgs, w_msgs):
        assert d["role"] == w["role"], f"role differs: {d['role']} vs {w['role']}"
        assert d["content"] == w["content"], (
            f"content differs for role={d['role']}\n"
            f"  desktop: {d['content']!r}\n  web:     {w['content']!r}"
        )
