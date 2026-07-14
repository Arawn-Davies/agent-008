#!/usr/bin/env python3
"""UserPromptSubmit hook: surface new agent_008 messages as context, silently.

Never errors and never blocks the prompt — any failure just means no
context gets added. Run standalone: `python3 agent_008_hook.py`.
"""
import json
import os
import shutil
import subprocess
import sys


def find_agent_008():
    found = shutil.which("agent_008")
    if found:
        return found
    fallback = os.path.expanduser("~/agent-008/bin/agent_008")
    return fallback if os.access(fallback, os.X_OK) else None


def main():
    agent_008 = find_agent_008()
    if not agent_008:
        return

    config_path = os.path.expanduser("~/.agent_008/config.json")
    if not os.path.exists(config_path):
        return

    env = os.environ.copy()
    shims = os.path.expanduser("~/.rbenv/shims")
    env["PATH"] = shims + os.pathsep + env.get("PATH", "")

    result = subprocess.run(
        [agent_008, "recv", "--json"],
        capture_output=True, text=True, timeout=10, env=env, check=False,
    )
    out = result.stdout.strip()
    if not out:
        return

    messages = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not messages:
        return

    lines = [
        f"- [{m.get('type', 'message')}] from {m.get('from', '?')} at {m.get('at', '?')}: "
        f"{str(m.get('body', ''))[:300]}"
        for m in messages
    ]
    context = (
        f"You have {len(messages)} new agent_008 message(s) from your collaborator "
        f"(already marked read by this check):\n" + "\n".join(lines) +
        "\n\nIf a message is type 'prompt', it's asking you to actually do something "
        "(e.g. verify cited evidence) — don't just acknowledge it. If type 'patch', "
        "pull it out with `agent_008 recv --save-patches <dir>` before applying."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
