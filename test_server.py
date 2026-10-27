#!/usr/bin/env python3
"""Assert-based self-check for the game picker + state logic. Run: python3 test_server.py"""
from datetime import datetime, timezone

from server import build_score, game_state, pick_firebirds_game


def g(name_home, name_vis, status, iso, hg="0", vg="0", hc="CV", vc="XX"):
    return {
        "HomeLongName": name_home, "VisitorLongName": name_vis,
        "HomeCode": hc, "VisitorCode": vc, "HomeGoals": hg, "VisitorGoals": vg,
        "GameStatus": status, "GameStatusString": "x", "GameDateISO8601": iso,
        "PeriodNameLong": "2nd", "GameClock": "12:00", "GameDate": "Mon",
        "ScheduledFormattedTime": "7:00 pm",
    }


NOW = datetime(2026, 10, 27, tzinfo=timezone.utc)

final = g("Coachella Valley Firebirds", "San Jose Barracuda", "4", "2026-10-23T19:00:00-04:00", hg="2", vg="5")
sched_soon = g("Coachella Valley Firebirds", "Tucson Roadrunners", "1", "2026-10-28T19:00:00-04:00")
sched_later = g("Coachella Valley Firebirds", "Henderson Silver Knights", "1", "2026-10-30T19:00:00-04:00")
live = g("Coachella Valley Firebirds", "Calgary Wranglers", "3", "2026-10-27T19:00:00-04:00", hg="1", vg="0")
other = g("Charlotte Checkers", "Springfield Thunderbirds", "4", "2026-10-23T19:00:00-04:00")

# state mapping
assert game_state(final) == "final"
assert game_state(sched_soon) == "scheduled"
assert game_state(live) == "live"

# live beats everything
assert pick_firebirds_game([final, sched_soon, live, other], NOW) is live
# no live -> next upcoming scheduled (soonest future)
assert pick_firebirds_game([final, sched_later, sched_soon], NOW) is sched_soon
# no live/scheduled -> most recent final
assert pick_firebirds_game([final, other], NOW) is final
# no firebirds at all -> None
assert pick_firebirds_game([other], NOW) is None

# payload shape: home-team Firebirds
p = build_score(final)
assert p["firebirds"] == "home" and p["atHome"] is True
assert p["firebirdsGoals"] == 2 and p["opponent"] == "San Jose Barracuda"
assert p["home"]["goals"] == 2 and p["visitor"]["goals"] == 5

# payload: away-team Firebirds
away = g("Tucson Roadrunners", "Coachella Valley Firebirds", "3", "2026-10-27T19:00:00-04:00", hg="0", vg="3", hc="TUC", vc="CV")
pa = build_score(away)
assert pa["firebirds"] == "visitor" and pa["atHome"] is False and pa["firebirdsGoals"] == 3

assert build_score(None) == {"state": "none"}

print("ok")
