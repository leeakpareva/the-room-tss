"""Inline the synthetic match dataset into the page and write dist/ (Static Web Apps root) and api/src/match.json."""
import json, pathlib, re, shutil

root = pathlib.Path(__file__).parent
DATASET = root.parent / "data" / "The_Room_Developer_Dataset_40_Player_v2.json"
COMMUNITY = "https://chat.whatsapp.com/LQpUvEsHq85KiyfltHiEkP"  # TSS WhatsApp community, from Seyi 27 Oct


def load_dataset():
    """Dataset v2 (40-player squads) with the one conflict Seyi's 27 Oct evening audit flagged fixed:
    Rafael Venn goes off at 90+1 (S09), so the 90+6 chance is his replacement Jude Arlen's."""
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    e19 = next(e for e in data["events"] if e["event_id"] == "E19")
    assert e19["player"] == "Rafael Venn", "dataset changed: check the E19 fix"
    e19.update(player="Jude Arlen", player_id="KSU19", facts="Arlen heads over from Kingsport's final set piece.")
    for n in data["narratives"]:
        if n["event_id"] == "E19":
            n.update(player="Jude Arlen", player_id="KSU19", facts=e19["facts"])
            n["commentary"] = re.sub(r"\bVenn\b", "Arlen", n["commentary"]).replace("فين", "آرلين")
    return data


def main():
    data = load_dataset()
    keep = ("event_id", "character", "language_code", "commentary")
    data["narratives"] = [{k: n[k] for k in keep} for n in data["narratives"]]
    data["stats"] = json.loads((root / "players.json").read_text(encoding="utf-8"))
    data["players"] = {t: [p for p in ps if p in data["stats"]["players"]] for t, ps in data["players"].items()}
    tr = root / "facts_i18n.json"
    data["facts_i18n"] = json.loads(tr.read_text(encoding="utf-8")) if tr.exists() else {}
    data["community"] = COMMUNITY
    for k in ("narratives_note", "qa"):
        data.pop(k, None)
    page = (root / "src" / "index.html").read_text(encoding="utf-8")
    body = page.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    shutil.copytree(root / "src" / "faces", dist / "faces", dirs_exist_ok=True)
    for f in ("tss-logo.png",):
        if (root / "src" / f).exists():
            shutil.copy(root / "src" / f, dist / f)
    # Static Web Apps serves a full document; the artifact skeleton is added only on artifact publish.
    (dist / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>The Room · TSS</title></head><body>\n'
        + body + "\n</body></html>\n", encoding="utf-8")

    # The API's copy: feed, squads and substitutions, English lines as voice examples, and every prepared line
    # (the only text /api/speak reads unsigned).
    api = {k: data[k] for k in ("match", "players", "events", "substitution_plan", "facts_i18n")}
    api["examples"] = {c: {n["event_id"]: n["commentary"] for n in data["narratives"] if n["character"] == c and n["language_code"] == "en"}
                       for c in data["match"]["characters"]}
    api["prepared"] = sorted({n["commentary"] for n in data["narratives"]})
    (root / "api" / "src" / "match.json").write_text(json.dumps(api, ensure_ascii=False), encoding="utf-8")
    print("built", len(body), "bytes;", sum(len(v) for v in data["players"].values()), "players in the table")


if __name__ == "__main__":
    main()
