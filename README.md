# Firebirds Scoreboard

A tiny web display for the **Coachella Valley Firebirds** (AHL). Shows the live
score during a game, the next scheduled game otherwise, and flashes a full-screen
**GOAL!** celebration (teal/red) when the Firebirds score. Built for a Raspberry
Pi driving a 7" (800×480) monitor.

No framework, no dependencies — just Python 3 standard library.

## Data source

Scores come from the AHL's public HockeyTech scorebar feed. `server.py` proxies
it at `/score` (the feed sends no browser CORS headers, so the page can't fetch
it directly). Keys are the public ones the league's own site uses.

## Run locally

```sh
python3 server.py
# open http://localhost:8000
```

```sh
python3 test_server.py   # self-check for the game-picker / state logic
```

## Deploy on the Raspberry Pi

Assumes Raspberry Pi OS with desktop and the repo at `/home/pi/firebirds-scoreboard`.

### 1. Run the server on boot (systemd)

```sh
sudo cp firebirds.service /etc/systemd/system/
sudo systemctl enable --now firebirds.service
systemctl status firebirds.service      # confirm it's running
curl -s localhost:8000/score            # confirm JSON
```

### 2. Launch Chromium in kiosk mode on boot

Raspberry Pi OS (Bookworm/Trixie) runs Wayland with the **labwc** compositor, so
the kiosk is started from labwc's autostart script — **as the user that logs into
the desktop** (not root, even if the server runs as root). Older X11
`~/.config/autostart/*.desktop` + `xset` instructions do not apply here.

As the desktop user:

```sh
mkdir -p ~/.config/labwc
cat > ~/.config/labwc/autostart <<'EOF'
chromium --kiosk --app=http://localhost:8000 --ozone-platform=wayland --noerrdialogs --disable-infobars &
EOF
```

The binary is `chromium` on Pi OS (not `chromium-browser`). A dedicated
scoreboard only needs this one line; delete the file to get the normal desktop
back.

### 3. Stop the screen from blanking

`xset` does nothing under Wayland. Use `sudo raspi-config` → Display Options →
Screen Blanking → **No**.

Reboot. Chromium should come up full-screen on the scoreboard.

## Notes / tuning

- Page polls `/score` every 15s (`POLL_MS` in `index.html`). The feed itself
  updates roughly once a minute during a game.
- `game_state()` in `server.py` maps the feed's `GameStatus`: `"1"` = scheduled,
  `"4"` = final, anything else = live. The exact in-progress code should be
  confirmed on a live game day and adjusted if needed.
- The goal flash fires when the Firebirds goal count increases between polls
  (never on first load).
