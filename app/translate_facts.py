"""Translate the 20 match-feed facts into the five other languages once, at build time, into facts_i18n.json.

The app shows these in 'Match facts', 'Moments that decided it' and The After, so a fan never sees English there.
Run with AOAI_ENDPOINT and AOAI_KEY set (the same Foundry deployment the API uses). Review the output before deploying.
"""
import json, os, pathlib, sys, urllib.request

root = pathlib.Path(__file__).parent
sys.path.insert(0, str(root))
from build import load_dataset  # noqa: E402

LANG = {"es": "Spanish", "fr": "French", "de": "German", "pt": "European Portuguese", "ar": "Modern Standard Arabic"}
ENDPOINT, KEY = os.environ["AOAI_ENDPOINT"].rstrip("/"), os.environ["AOAI_KEY"]
DEPLOYMENT = os.environ.get("AOAI_DEPLOYMENT", "gpt-41-mini")


def chat(system, user):
    req = urllib.request.Request(
        f"{ENDPOINT}/openai/deployments/{DEPLOYMENT}/chat/completions?api-version=2024-10-21",
        data=json.dumps({"messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                         "temperature": 0, "response_format": {"type": "json_object"}}).encode(),
        headers={"api-key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(json.loads(r.read())["choices"][0]["message"]["content"])


def main():
    events = load_dataset()["events"]
    src = {e["event_id"]: e["facts"] for e in events}
    subs = {e["event_id"]: f'{e["player_on"]} comes ON, {e["player_off"]} goes OFF' for e in events if e.get("player_on")}
    out = {}
    for code, name in LANG.items():
        got = chat(
            f"Translate football match facts from English into {name}. Keep every player, club and team name exactly as written. "
            "Keep every number and minute. Keep the meaning exact: for a substitution, the player who comes on and the one who goes "
            "off must not swap. Plain, calm match-report style. Reply with JSON: the same keys, translated values.",
            json.dumps({"facts": src, "substitution_check": subs}, ensure_ascii=False))
        out[code] = got.get("facts", got)
        assert set(out[code]) == set(src), f"{code}: keys differ"
        print(code, "done")
    (root / "facts_i18n.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
