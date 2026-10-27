"""Write players.json: synthetic tracking for every player who took part in CC-DEM-001 (dataset v2, 40-player squads).

Minutes on and off come from the dataset's substitution plan and red card, so the card always agrees with the feed.
Volume stats are full-match totals, seeded from the player's id so the numbers are stable between builds.
Goals, assists, saves and cards are not stored here: the app counts them from the event feed.
"""
import hashlib, json, pathlib, sys

root = pathlib.Path(__file__).parent
sys.path.insert(0, str(root))
from build import load_dataset  # noqa: E402

GROUP = {"GK": "GK", "RB": "DEF", "CB": "DEF", "LB": "DEF", "FB": "DEF",
         "DM": "MID", "CM": "MID", "AM": "MID", "RW": "WIDE", "LW": "WIDE", "ST": "FWD", "FW": "FWD"}
POS = {"GK": "Goalkeeper", "RB": "Right-back", "CB": "Centre-back", "LB": "Left-back", "FB": "Full-back",
       "DM": "Defensive midfielder", "CM": "Central midfielder", "AM": "Attacking midfielder",
       "RW": "Right winger", "LW": "Left winger", "ST": "Striker", "FW": "Forward"}
# [low, high] per full match, by group
RANGE = {
    "GK":   {"touches": (28, 38), "km": (4.8, 5.6), "claims": (2, 6), "distribution": (68, 82)},
    "DEF":  {"touches": (52, 74), "km": (9.6, 10.8), "tackles": (2, 5), "interceptions": (1, 4), "clearances": (3, 8), "duels": (4, 9)},
    "MID":  {"touches": (58, 84), "km": (10.6, 12.2), "passes": (38, 66), "pass_pct": (81, 91), "key_passes": (1, 3), "tackles": (1, 4)},
    "WIDE": {"touches": (36, 52), "km": (10.2, 11.6), "crosses": (4, 9), "crosses_done": (1, 3), "dribbles": (2, 5)},
    "FWD":  {"touches": (30, 44), "km": (9.4, 10.6), "shots": (2, 4), "on_target": (1, 2), "aerials": (2, 5)},
}
PCT = {"distribution", "pass_pct"}  # rates, not scaled by minutes


def minute(m):
    return 96 if m == "FT" else sum(int(x) for x in m.replace(":00", "").split("+"))


def pick(pid, key, lo, hi):
    r = int(hashlib.sha256(f"{pid}|{key}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    v = lo + (hi - lo) * r
    return round(v, 1) if isinstance(lo, float) else round(v)


def main():
    data = load_dataset()
    off = {s["player_off"]: minute(s["minute"]) for s in data["substitution_plan"]}
    on = {s["player_on"]: minute(s["minute"]) for s in data["substitution_plan"]}
    for e in data["events"]:
        if e["event_type"] == "RED_CARD":
            off[e["player"]] = minute(e["minute"])
    players = {}
    for team, squad in data["matchday_squads"].items():
        for p in squad:
            n = p["name"]
            if p["squad_role"] == "substitute" and n not in on:
                continue  # unused substitute: took no part
            g = GROUP[p["position"]]
            s = {"pos": POS[p["position"]], "group": g, "shirt": p["shirt_number"], "on": on.get(n, 0), "off": off.get(n, 96)}
            share = (s["off"] - s["on"]) / 96
            for k, (lo, hi) in RANGE[g].items():
                v = pick(p["player_id"], k, lo, hi)
                # totals are for the player's own minutes; rates stay as they are
                s[k] = v if k in PCT else round(v * share, 1) if k == "km" else round(v * share)
            if g == "FWD":
                s["on_target"] = min(s["on_target"], s["shots"])
            if g == "WIDE":
                s["crosses_done"] = min(s["crosses_done"], s["crosses"])
            players[n] = s
    out = {
        "note": "Synthetic tracking data for the fictional match CC-DEM-001 (dataset v2, 40-player squads), written to agree "
                "with the event feed: minutes on and off follow the substitution plan and the red card. Volume stats are "
                "full-match totals; the app shows them pro rata to the minute. Goals, assists, saves and cards are counted "
                "from the feed.",
        "groups": {
            "GK": [["saves", "Saves"], ["conceded", "Goals conceded"], ["claims", "High balls claimed"], ["distribution", "Distribution %"]],
            "DEF": [["tackles", "Tackles won"], ["interceptions", "Interceptions"], ["clearances", "Clearances"], ["duels", "Duels won"]],
            "MID": [["passes", "Passes"], ["pass_pct", "Pass accuracy %"], ["key_passes", "Key passes"], ["tackles", "Tackles won"]],
            "WIDE": [["crosses", "Crosses"], ["crosses_done", "Crosses found a man"], ["dribbles", "Dribbles won"], ["assists", "Assists"]],
            "FWD": [["shots", "Shots"], ["on_target", "On target"], ["goals", "Goals"], ["aerials", "Aerial duels won"]],
        },
        "players": players,
    }
    (root / "players.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("players.json:", len(players), "players took part")


if __name__ == "__main__":
    main()
