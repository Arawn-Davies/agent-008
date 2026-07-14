# CLAUDE.md — agent_im self-install

If you (an AI coding agent) have been pointed at this repo and asked to
"set up agent_im" or "install this," work through the steps below in order.
Each has a verification check — don't move to the next step until the
current one's check passes. Full human-readable docs are in `README.md`;
this file is the condensed, do-it-now version for an agent driving the
install itself. Ask the user (don't guess) wherever a step says to.

## 0. Figure out the OS

`uname -s` → `Linux` or `Darwin`. Steps below branch on this.

## 1. Tailscale

Check: `command -v tailscale && tailscale status`.

If missing, install it:
- Linux: `curl -fsSL https://tailscale.com/install.sh | sh` (needs sudo —
  ask the user to run it themselves if you can't sudo non-interactively).
- macOS: `brew install tailscale && sudo brew services start tailscale`.

Then: `tailscale up`. **This opens a browser login — you cannot complete
this step yourself.** Tell the user to run `tailscale up` and finish the
login, then continue once `tailscale ip -4` prints an address.

**Ask the user for the peer's Tailscale IP** (their collaborator's
`tailscale ip -4` output) — you have no way to discover it yourself.

## 2. Ruby 3.1+ on the host (not inside a project's Docker container)

Check: `ruby -v` shows 3.1+ from a real interactive shell. If there's no
system Ruby and no rbenv:
- Linux: `sudo apt-get install -y rbenv ruby-build` (needs sudo — same
  caveat as above).
- macOS: `brew install rbenv ruby-build`.

Then: `rbenv install 3.1.2 && rbenv global 3.1.2` (any recent 3.1.x is
fine — this app is stdlib-only, no gem/version sensitivity). Confirm
`rbenv init` got added to `~/.bashrc` (Linux) or `~/.zshrc` (macOS) — it's
usually automatic, add it if not. **rbenv only takes effect in a new
interactive shell** — when testing subsequent steps yourself in this
session, prepend `~/.rbenv/shims` to `PATH` explicitly rather than relying
on shell rc files, since non-interactive shells skip them.

## 3. This repo + PATH

If you're not already running from a clone of this repo, clone it:
`git clone https://github.com/Arawn-Davies/agent-008.git ~/agent-008`.

Confirm `chmod +x ~/agent-008/bin/agent_im ~/agent-008/bin/agent_im_hook.py`
(should already be executable from git, verify with `git ls-files -s`).

Add `~/agent-008/bin` to `PATH` in the user's shell rc file
(`~/.bashrc`/`~/.zshrc`) if it isn't already.

## 4. Configure agent_im

**Ask the user for:** the peer's Tailscale IP (from step 1) and what name
they want to go by. Then:
```
~/.rbenv/shims/ruby ~/agent-008/bin/agent_im init --peer <peer-ip>:8420 --name <name>
```
Verify: `cat ~/.agent_im/config.json` shows the right peer/name.

## 5. Start `serve`, persistently

A foreground `agent_im serve` only lasts as long as the terminal does —
install it as a real background service instead:

- **Linux (systemd user service):**
  ```
  mkdir -p ~/.config/systemd/user
  cp ~/agent-008/contrib/agent_im.service ~/.config/systemd/user/
  systemctl --user enable --now agent_im
  systemctl --user status agent_im   # verify: active (running)
  ```

- **macOS (launchd):** edit `~/agent-008/contrib/com.agentim.serve.plist`
  first — replace every `/Users/YOURNAME` with the real home directory
  (plists don't expand `~`), and confirm the ruby path with
  `rbenv which ruby`. Then:
  ```
  cp ~/agent-008/contrib/com.agentim.serve.plist ~/Library/LaunchAgents/
  launchctl load ~/Library/LaunchAgents/com.agentim.serve.plist
  launchctl list | grep com.agentim.serve   # verify it's listed
  ```

Verify end-to-end: from the OTHER machine (or `--bind 127.0.0.1` locally
for a quick self-test), `agent_im send "install check"` should succeed, and
this machine's `agent_im recv` should show it.

## 6. Install the Claude Code integration (skill + hook)

These make Claude Code itself use agent_im, not just the human on the CLI.

**Skill** — copy it into place:
```
mkdir -p ~/.claude/skills/agentim
cp ~/agent-008/claude-integration/SKILL.md ~/.claude/skills/agentim/SKILL.md
```

**Hook** — merge `claude-integration/hook-settings-snippet.json`'s `hooks`
key into `~/.claude/settings.json`. **Read the existing file first and
merge, don't overwrite** — if it already has a `hooks.UserPromptSubmit`
array, append this hook's object to that array rather than replacing it.
If `~/.claude/settings.json` doesn't exist yet, the snippet file can be
copied as-is.

Verify: `echo '{}' | python3 ~/agent-008/bin/agent_im_hook.py` should print
nothing (no messages yet) without erroring.

## 7. Tell the user what's left

You cannot do these — say so explicitly rather than trying:
- If step 1's `tailscale up` login wasn't already done, it still needs
  doing.
- Actually talking to their collaborator to exchange Tailscale IPs, if
  that hasn't happened yet.
- Starting a `/loop 1m /agent_im watch` session is a per-session choice,
  not part of install — mention it, don't start it unprompted.
