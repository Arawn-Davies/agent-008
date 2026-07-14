---
name: agentim
description: Send and check messages between two Claude Code agents run by different people, using agent_im — a small Ruby CLI tunneled directly over Tailscale (no third-party service). Use whenever the user wants to notify a collaborator's agent that work is done and needs verification, wants to check for incoming messages/patches/prompts from a collaborator, wants to send a patch/diff for the other side to review or apply, or is setting up/troubleshooting cross-machine agent coordination. Triggers on phrases like "ping my collaborator's agent", "check for messages", "send them this diff", "did they reply yet", "send a verify request", or being asked to run as a watcher/loop that reacts to a collaborator's agent.
---

# agentim — instant messenger for agents

A thin messaging layer so two independently-running Claude Code agents
(different people, different machines, different Claude accounts) can tell
each other "I finished X, here's the evidence, please verify," share a
patch, or ask a direct question — without a human manually relaying
messages between them.

The actual tool is `agent_im`, a standalone Ruby CLI that lives in its own
repo: **https://github.com/Arawn-Davies/agent-008** (cloned to `~/agent-008`
by convention, ideally with `~/agent-008/bin` on `PATH` — see that repo's
README for full install/setup). This skill is the *usage* layer on top of
it — don't reimplement any of this with ad hoc `curl`/`nc` calls, and don't
guess at flags; run `agent_im help` for the authoritative reference if
anything here seems out of date with the installed version.

It is not tied to any one codebase — pass whatever a project uses (ticket
ids, `file:line` citations, a `git diff`) through as plain message content.

## How it works

`agent_im serve` runs a tiny HTTP server bound **only** to your Tailscale
IP (nothing off the tailnet can reach it) and appends every incoming
message to a local file, `~/.agent_im/inbox.jsonl`. `agent_im send` POSTs
straight to the peer's Tailscale IP — no GitHub, no public broker, no
polling of a third party. If the peer's `serve` isn't reachable right now,
`send` queues the message to a local outbox and retries automatically (via
`flush` or the next `watch`) instead of dropping it.

```
agent_im send ("<text>" | -) [--type message|patch|prompt]
agent_im send --patch <file>          # shorthand for --type patch
agent_im send --diff                  # shorthand: body = `git diff` here
agent_im recv [--all] [--json] [--save-patches DIR]
agent_im watch                        # one poll pass: flush outbox + check inbox
agent_im flush                        # retry queued/undelivered messages
agent_im outbox                       # list what's still queued
agent_im chat                         # plain human-to-human REPL, same tunnel
```

Run `agent_im help` for the full flag reference.

**Prerequisite check before first use:** confirm `agent_im` is on `PATH`
(`command -v agent_im`) and that `~/.agent_im/config.json` exists
(`agent_im` will tell you to run `init` if not). If either is missing,
point the user at `~/agent-008/README.md` rather than trying to reinvent
setup — it covers Tailscale + rbenv install for both Ubuntu and macOS.

## Sending a message

Pick the right `--type` — it's how the receiving side (and its `watch`
loop) knows what kind of attention the message needs:

- `message` (default) — status update / FYI, e.g. "done with X".
- `prompt` — a specific ask that needs the other agent to actually do
  something (not just note it), e.g. "please verify these citations."
- `patch` — a diff. Use `--diff` (sends `git diff` from the current repo)
  or `--patch <file>` (sends an existing `.patch`/`.diff` file) rather than
  pasting diff text as a plain message — this lets the receiver
  `agent_im recv --save-patches <dir>` straight to an applyable file.

Always cite real evidence in the body — a `file:line`, a command's actual
output, a commit SHA — never a vague "should be fine now." An unverifiable
claim is worse than no claim, because it looks like proof.

```
agent_im send --type prompt "Fixed contrast-input-borders on task_templates#index, evidence at app/assets/stylesheets/examtrack/application.css:88 — please verify"
```

## Checking for messages — and what to do with a prompt/patch

Run `agent_im recv` (or `agent_im watch` in a loop — see below). It only
shows messages since you last read them (a local cursor, no network call),
so it's safe to run often.

**When a `prompt` type message asks you to verify something, actually
verify it — don't rubber-stamp the sender's word.** Open every cited
file:line yourself and confirm it says what the message claims. If the
project has its own verification tooling (e.g. this repo's `curbcut
verify`, a test suite, a linter), run that too. Only then reply — plainly
state what you checked and what you found, confirming or specifically
disputing the claim (a rejection without a specific counter-citation is as
useless as an unverified pass).

**When a `patch` type message arrives**, pull it out with
`agent_im recv --save-patches /tmp/agentim-patches` and review it like any
other diff before applying (`git apply <file>`, or `git apply --check
<file>` first to dry-run) — receiving a patch from a trusted collaborator's
agent doesn't exempt it from the same read-before-apply discipline as any
other code change.

This mirrors a simple rule worth stating plainly: **a pass one agent
records about its own work is provisional until a different agent, working
independently, confirms it.** Don't skip the independent check because the
sender sounds confident, and don't mark something verified from memory of
an earlier look — re-open the files fresh each time.

## Running it as a watcher (the "automatic ping" part)

Claude Code agents aren't background daemons — nothing pings you while no
session is running. `agent_im serve` itself needs to be a long-lived
process (started via nohup/tmux/the systemd or launchd templates in
`agent-008/contrib/`) for the *peer's* messages to reach your machine at
all. On top of that, driving `agent_im watch` on a short interval via the
`/loop` skill is what makes your *agent* actually notice and react while
you're working:

```
/loop 1m /agent_im watch
```

Each wake flushes any queued outbound messages and checks the inbox; if
`watch` reports new messages, act on them immediately (verify, apply a
patch, reply) before the loop reschedules — don't just acknowledge and wait
for the next prompt.

If a `UserPromptSubmit` hook is configured (see the project's
`.claude/settings.json`), new messages also get surfaced automatically at
the start of each turn even without a loop running — check for one before
assuming you need to start `/loop` yourself.

## Hygiene

- `agent_im outbox` before assuming a message got through — an unreachable
  peer means it's queued, not lost, but it's still undelivered until
  flushed.
- `agent_im chat` is for direct human-to-human conversation over the same
  tunnel (e.g. the two people quickly hashing something out) — it doesn't
  touch the `recv` cursor, so using it never causes an agent's `watch` to
  miss or skip a structured message.
- Keep message bodies self-contained — the receiving agent has no memory of
  your session, so a citation like "app/models/foo.rb:42" is useful, "the
  thing we discussed" is not.
