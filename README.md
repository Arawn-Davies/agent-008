# agent_im

A tiny instant messenger for two Claude Code agents running on different
machines/accounts, tunneled directly over [Tailscale](https://tailscale.com).
No GitHub, no third-party message broker — one side runs `agent_im serve`
(bound only to its Tailscale IP), the other `send`s straight to it, and both
sides `recv`/`watch` a local inbox file.

```mermaid
flowchart LR
    subgraph You["Your machine"]
        YS["agent_im send"]
        YSrv["agent_im serve\n(bound to your Tailscale IP)"]
        YInbox[("inbox.jsonl")]
        YR["agent_im recv / watch"]
        YSrv --> YInbox --> YR
    end

    subgraph Them["Their machine"]
        TS["agent_im send"]
        TSrv["agent_im serve\n(bound to their Tailscale IP)"]
        TInbox[("inbox.jsonl")]
        TR["agent_im recv / watch"]
        TSrv --> TInbox --> TR
    end

    YS -- Tailscale tunnel --> TSrv
    TS -- Tailscale tunnel --> YSrv
```

Nothing here is Rails/RadSystem-specific — it's a general-purpose CLI, usable
from any project.

## Prerequisites

1. **Both machines on the same Tailscale network (tailnet).**

   **Ubuntu/Debian:**
   ```
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

   **macOS:**
   ```
   brew install tailscale
   sudo brew services start tailscale   # runs tailscaled in the background
   tailscale up
   ```
   (Alternatively, install the Tailscale app from the Mac App Store /
   tailscale.com — then enable Settings → "Install command line tool" to get
   the `tailscale` CLI.)

   Either way, `tailscale up` opens a browser login — sign in (or accept an
   invite to a shared tailnet if one already exists). Confirm it worked:
   ```
   tailscale ip -4     # prints your 100.x.y.z tailnet address
   ```
   Both people need to know each other's address — share it out of band.

2. **Ruby 3.1+ on the host** (not inside a project's Docker container — this
   tool needs to run standalone). [rbenv](https://github.com/rbenv/rbenv) is
   the easiest way if you don't already have a system Ruby:

   **Ubuntu/Debian:**
   ```
   sudo apt-get install -y rbenv ruby-build
   rbenv install 3.1.2        # any recent 3.1.x is fine, agent_im has no
   rbenv global 3.1.2         # exact-version dependency — stdlib only
   ```
   This wires `eval "$(rbenv init - bash)"` into `~/.bashrc` automatically.

   **macOS:**
   ```
   brew install rbenv ruby-build
   rbenv install 3.1.2
   rbenv global 3.1.2
   echo 'eval "$(rbenv init - zsh)"' >> ~/.zshrc   # bash: use `- bash` and ~/.bash_profile
   ```

   Either way, rbenv only takes effect in a **new interactive shell** —
   open a fresh terminal after installing, then confirm:
   ```
   ruby -v   # should print the rbenv-managed version, not a system one
   ```

No gems to install — `agent_im` only uses Ruby's standard library
(`socket`, `net/http`, `json`, `optparse`), so `bundle install` isn't needed.

## Install

```
git clone https://github.com/Arawn-Davies/agent-008.git ~/agent-008
chmod +x ~/agent-008/bin/agent_im     # should already be executable from git
```

Put it on your `PATH` (add to `~/.bashrc` / `~/.zshrc`), or just invoke it by
full path — both work:
```
export PATH="$HOME/agent-008/bin:$PATH"
```

## Setup

Each person configures their own peer (the *other* person's Tailscale
address, found via `tailscale ip -4` on their machine):

```
agent_im init --peer <their-tailscale-ip>[:8420] --name <your-name>
```

The two of you mirror this — each points `--peer` at the *other's* address
and `--name` at their *own*. Config lands in `~/.agent_im/config.json`.
Default port is `8420` — change with `--port` on both `init` and `serve` if
it's taken.

## Running it

**Start your mailbox server** (must be running for the *other* person's
messages to reach you — this is a `serve`, not a one-shot command, so leave
it running):

```
agent_im serve
```

It binds **only** to your Tailscale IP (auto-detected via `tailscale ip -4`,
override with `--bind`), never `0.0.0.0` — so nothing outside your tailnet
can ever reach it, on purpose.

To keep it running in the background instead of tying up a terminal:
```
nohup agent_im serve > ~/.agent_im/serve.log 2>&1 &
```
or, more durably, run it as a background service that survives reboots/logout:

**Ubuntu/Debian (systemd user service)** — template at `contrib/agent_im.service`:
```
mkdir -p ~/.config/systemd/user
cp ~/agent-008/contrib/agent_im.service ~/.config/systemd/user/
systemctl --user enable --now agent_im
journalctl --user -u agent_im -f   # tail its output
```

**macOS (launchd)** — template at `contrib/com.agentim.serve.plist`:
```
cp ~/agent-008/contrib/com.agentim.serve.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.agentim.serve.plist
tail -f ~/.agent_im/serve.log
```

**Send a message:**
```
agent_im send "Fixed contrast-input-borders on task_templates#index, evidence at application.css:88 — please verify"
```
or pipe in longer content (no size limit imposed by a third party — it's a
direct POST over the tunnel):
```
curbcut show task_templates-index --json | agent_im send -
```

**Check your inbox** (polls the local file `serve` has been writing to —
this does *not* hit the network, it's instant and free to call often):
```
agent_im recv            # only messages since you last checked
agent_im recv --all      # replay everything
agent_im recv --json     # one JSON object per message, for scripting
```

**Automatic pickup while actively working:** drive `agent_im watch` (one
poll pass, always exits 0) with Claude Code's `/loop` skill:
```
/loop 1m /agent_im watch
```
Whichever side has this loop running will notice a new message within about
a minute and can act on it (e.g. verify cited evidence, then `agent_im send`
a reply) without a human re-prompting.

## Files

| Path                        | What                                              |
|------------------------------|---------------------------------------------------|
| `~/.agent_im/config.json`    | your name, peer address, listen port              |
| `~/.agent_im/inbox.jsonl`    | append-only log of every message you've received  |
| `~/.agent_im/state`          | cursor — how far `recv` has already read          |

## Security model

Tailscale is the security boundary: `serve` binds to your tailnet IP only,
so reachability is already restricted to devices on your tailnet (encrypted,
device-authenticated by Tailscale). There's no additional auth token on top
— if your tailnet has more than the two of you on it, anyone else on it can
also reach the port, so keep the tailnet scoped accordingly if that matters.

## Troubleshooting

- **`can't reach <peer>`**: confirm `tailscale status` shows the peer as
  connected, confirm *they* have `agent_im serve` actually running, confirm
  you used their current `tailscale ip -4` (it can change if they re-auth).
- **`ruby -v` shows a system Ruby, not rbenv's**: open a new terminal (rbenv
  wires into interactive shells via `~/.bashrc`, which non-interactive
  shells skip on purpose).
