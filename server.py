#!/usr/bin/env python3
"""Tiny stdlib-only scoreboard server for the Coachella Valley Firebirds.

Serves index.html and a /score JSON endpoint that proxies the AHL HockeyTech
scorebar feed (the feed sends no browser CORS headers, so we can't fetch it
straight from the page). No framework, no dependencies.
"""
import json
import re
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8000
TEAM = "Firebirds"  # matches HomeLongName / VisitorLongName
FEED_URL = (
    "https://lscluster.hockeytech.com/feed/index.php"
    "?feed=modulekit&view=scorebar"
    "&numberofdaysback=2&numberofdaysahead=30"
    "&key=ccb91f29d6744675&client_code=ahl"
)
HERE = Path(__file__).parent


def game_state(game):
    """Map HockeyTech GameStatus to our state.

    Verified against the live feed: "1" = scheduled (string holds start time),
    "4" = Final. In-progress games report other codes (2/3); treat anything
    that isn't scheduled or final as live.
    ponytail: confirm the exact in-progress code on a real game day.
    """
    status = game.get("GameStatus")
    if status == "1":
        return "scheduled"
    if status == "4":
        return "final"
    return "live"


def _dt(game):
    return datetime.fromisoformat(game["GameDateISO8601"])


def pick_firebirds_game(games, now):
    """Pick the game to show: a live one, else next scheduled, else last final."""
    fb = [g for g in games if TEAM in g["HomeLongName"] or TEAM in g["VisitorLongName"]]
    if not fb:
        return None
    live = [g for g in fb if game_state(g) == "live"]
    if live:
        return max(live, key=_dt)
    scheduled = sorted((g for g in fb if game_state(g) == "scheduled"), key=_dt)
    upcoming = [g for g in scheduled if _dt(g) >= now]
    if upcoming:
        return upcoming[0]
    if scheduled:
        return scheduled[-1]
    finals = [g for g in fb if game_state(g) == "final"]
    if finals:
        return max(finals, key=_dt)
    return None


def big_logo(url):
    """Feed logos are 50x50 (…/logos/50x50/445.png); the full-res 500x500 lives
    at …/logos/445.png. Drop the size segment to upgrade."""
    return re.sub(r"/\d+x\d+/", "/", url) if url else ""


def build_score(game):
    """Shape a feed game into the small payload the page consumes."""
    if game is None:
        return {"state": "none"}
    home = {
        "name": game["HomeLongName"],
        "code": game["HomeCode"],
        "goals": int(game["HomeGoals"]),
        "logo": big_logo(game.get("HomeLogo", "")),
    }
    visitor = {
        "name": game["VisitorLongName"],
        "code": game["VisitorCode"],
        "goals": int(game["VisitorGoals"]),
        "logo": big_logo(game.get("VisitorLogo", "")),
    }
    firebirds = "home" if TEAM in game["HomeLongName"] else "visitor"
    opponent = visitor if firebirds == "home" else home
    return {
        "state": game_state(game),
        "home": home,
        "visitor": visitor,
        "firebirds": firebirds,
        "firebirdsGoals": (home if firebirds == "home" else visitor)["goals"],
        "opponent": opponent["name"],
        "atHome": firebirds == "home",
        "period": game.get("PeriodNameLong", ""),
        "clock": game.get("GameClock", ""),
        "dateISO": game.get("GameDateISO8601", ""),
        "startTime": game.get("ScheduledFormattedTime", ""),
        "gameDate": game.get("GameDate", ""),
        "statusString": game.get("GameStatusString", ""),
    }


def fetch_score():
    with urllib.request.urlopen(FEED_URL, timeout=10) as resp:
        games = json.load(resp)["SiteKit"]["Scorebar"]
    return build_score(pick_firebirds_game(games, datetime.now(timezone.utc)))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] == "/score":
            try:
                body = json.dumps(fetch_score()).encode()
            except Exception as e:  # feed down / network blip -> let the page retry
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            try:
                body = (HERE / "index.html").read_bytes()
            except FileNotFoundError:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *args):  # quiet
        pass


if __name__ == "__main__":
    print(f"Firebirds scoreboard on http://localhost:{PORT}")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
