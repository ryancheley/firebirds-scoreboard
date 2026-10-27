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

Assumes Raspberry Pi OS with desktop. Paths below use `<user>` for your login
and `<repo>` for the clone location (e.g. `/home/<user>/firebirds-scoreboard`);
substitute your own. Match the `User=`/`WorkingDirectory=` in `firebirds.service`
to wherever you cloned it.

### 1. Run the server on boot (systemd)

```sh
sudo cp firebirds.service /etc/systemd/system/
sudo systemctl enable --now firebirds.service
systemctl status firebirds.service      # confirm it's running
curl -s localhost:8000/score            # confirm JSON
```

### 2. Launch Chromium in kiosk mode on boot

Raspberry Pi OS (Bookworm/Trixie) runs Wayland with the **labwc** compositor, so
the kiosk is started from labwc's autostart script, as the user that logs into
the desktop (not root, even if the server runs as root). Older X11
`~/.config/autostart/*.desktop` + `xset` instructions do not apply here.

Needs `grim` (Wayland screenshot tool) for the self-heal check below:
`sudo apt-get install -y grim`.

As the desktop user:

```sh
mkdir -p ~/.config/labwc
cat > ~/.config/labwc/autostart <<'EOF'
# wait until the scoreboard server is answering
while ! curl -sf http://localhost:8000/score >/dev/null; do sleep 1; done

# labwc + Chromium bug: the FIRST toplevel on a fresh session renders a stuck
# white frame and never repaints; relaunching fixes it. So launch, then check
# the real screen with grim and relaunch until the scoreboard actually paints.
LAUNCH="chromium --kiosk http://localhost:8000 --ozone-platform=wayland --password-store=basic --disable-session-crashed-bubble --noerrdialogs --disable-infobars --start-fullscreen"
$LAUNCH &
for i in $(seq 1 12); do
  sleep 25
  grim /tmp/kiosk_check.png 2>/dev/null || continue
  sz=$(stat -c %s /tmp/kiosk_check.png 2>/dev/null || echo 0)
  # white ~2KB, desktop wallpaper ~290KB, scoreboard (mostly black) ~15-60KB
  if [ "$sz" -gt 6000 ] && [ "$sz" -lt 120000 ]; then break; fi
  pkill chromium; sleep 3; $LAUNCH &
done
EOF
```

The binary is `chromium` on Pi OS (not `chromium-browser`). Notes:

- The first `while` loop waits for the server so Chromium doesn't load before the
  port is up.
- **The self-heal loop is the important part.** On labwc the very first Chromium
  window comes up as a stuck white frame and never repaints — load settling
  doesn't help, only a relaunch does. The loop screenshots the screen with `grim`
  and relaunches until the scoreboard paints (verified on real hardware: a slow
  Pi reaches the scoreboard unattended ~3–4 min after boot).
- Plain `--kiosk <url>`, not `--app=` (which also renders white under Wayland).
- `--password-store=basic` suppresses the gnome-keyring password prompt on boot.
- `--disable-session-crashed-bubble` avoids the "restore pages" page after an
  unclean shutdown.
- Do **not** add `--disable-gpu`: Pi OS wraps Chromium with `--use-angle=gles`
  and `--enable-gpu-rasterization`, and forcing `--disable-gpu` on top is another
  white-screen cause. Let the GPU path run.

A dedicated scoreboard only needs this file; delete it to get the normal desktop
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
