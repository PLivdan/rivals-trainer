from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

BANNERS = {
    "deadpool": "data/heroes/deadpool/portraits/banner.jpg",
}


def canon_cd(s: str):
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*s(?:ec|econds)?\b", s)
    if not m:
        return None
    val = float(m.group(1))
    return int(val) if val.is_integer() else val


def pick_stat(stats: dict, want, exclude=()):
    for k, v in stats.items():
        kl = k.lower()
        if any(w in kl for w in want) and not any(x in kl for x in exclude):
            return v
    return None


DMG_X = ("falloff", "boost", "shar", "reduc", "increas", "taken",
         "resist", "amplif", "bonus", "over time")
HEAL_X = ("cooldown", "boost", "increas")
DUR_X = ("cooldown",)


def first_icon(hero) -> str | None:
    for a in hero["abilities"]:
        if a.get("icon_file"):
            return "data/heroes/" + a["icon_file"]
    return None


def build():
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    heroes = []
    for h in idx:
        d = json.loads((DATA / "heroes" / h["slug"] / "data.json").read_text(encoding="utf-8"))
        abilities = []
        for a in d["abilities"]:
            if not a.get("icon_file"):
                continue
            st = a["stats"]
            cd_disp = st.get("Cooldown")
            dmg = st.get("Damage") or pick_stat(st, ("damage",), DMG_X)
            heal = pick_stat(st, ("healing", "health recovery"), HEAL_X)
            dur = pick_stat(st, ("duration", "invisib", "stealth"), DUR_X)
            abilities.append({
                "name": a["name"],
                "key": a["key"],
                "slot": a["slot"],
                "desc": a["description"],
                "icon": "data/heroes/" + a["icon_file"],
                "cd": canon_cd(cd_disp),
                "cd_text": cd_disp,
                "charge": bool(cd_disp and "charge" in cd_disp.lower()),
                "dmg": dmg,
                "heal": heal,
                "dur": dur,
                "stats": {k: v for k, v in (a["stats"] or {}).items() if k != "Key"},
            })
        teamups = []
        for t in d["team_ups"]["provided"]:
            ts = {**(t["base"]["stats"] or {}), **(t["enhanced"]["stats"] or {})}
            cd_disp = ts.get("Cooldown")
            dmg = ts.get("Damage") or pick_stat(ts, ("damage",), DMG_X)
            heal = pick_stat(ts, ("healing", "health recovery"), HEAL_X)
            dur = pick_stat(ts, ("duration", "invisib", "stealth"), DUR_X)
            teamups.append({
                "name": t["name"],
                "partner": t.get("partner", ""),
                "icon": ("data/heroes/" + t["icon_file"]) if t.get("icon_file") else None,
                "base": t["base"]["description"],
                "enhanced": t["enhanced"]["description"],
                "cd": canon_cd(cd_disp),
                "cd_text": cd_disp,
                "charge": bool(cd_disp and "charge" in cd_disp.lower()),
                "dmg": dmg,
                "heal": heal,
                "dur": dur,
                "base_stats": {k: v for k, v in (t["base"]["stats"] or {}).items() if k != "Key"},
                "enh_stats": {k: v for k, v in (t["enhanced"]["stats"] or {}).items() if k != "Key"},
            })
        received = [{
            "name": t["name"],
            "desc": t["description"],
            "icon": ("data/heroes/" + t["icon_file"]) if t.get("icon_file") else None,
        } for t in d["team_ups"]["received"]]

        portrait = BANNERS.get(h["slug"])
        if not portrait and d.get("portrait_files"):
            portrait = "data/heroes/" + d["portrait_files"][-1]

        icon_path = DATA / "heroes" / h["slug"] / "icon.png"
        heroes.append({
            "slug": h["slug"],
            "name": d["name"],
            "role": d["role"].title(),
            "desc": d["description"],
            "health": d["base_stats"].get("Health", ""),
            "thumb": portrait or first_icon(d),
            "icon": ("data/heroes/" + h["slug"] + "/icon.png") if icon_path.exists() else None,
            "abilities": abilities,
            "teamups": teamups,
            "received": received,
        })

    def norm(s):
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    name2slug = {norm(h["name"]): h["slug"] for h in heroes}
    icon_by_slug = {h["slug"]: h["icon"] for h in heroes}
    name_by_slug = {h["slug"]: h["name"] for h in heroes}

    def resolve(partner: str):
        p = norm(partner)
        if p and p in name2slug:
            return name2slug[p]
        return None

    names_sorted = sorted({h["name"] for h in heroes}, key=len, reverse=True)
    hero_re = re.compile(r"\b(" + "|".join(re.escape(n) for n in names_sorted) + r")\b", re.I)

    def search_partner(self_slug, *texts):
        for text in texts:
            for m in hero_re.finditer(text or ""):
                sl = name2slug.get(norm(m.group(1)))
                if sl and sl != self_slug:
                    return sl
        return None

    for h in heroes:
        for t in h["teamups"]:
            sl = resolve(t.get("partner", "")) or search_partner(
                h["slug"], t["enhanced"], t["base"])
            t["partner_slug"] = sl
            t["partner_icon"] = icon_by_slug.get(sl) if sl else None
            if sl:
                t["partner"] = name_by_slug[sl]

    out = {"heroes": heroes}
    (ROOT / "site_data.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n_ab = sum(len(h["abilities"]) for h in heroes)
    n_cd = sum(1 for h in heroes for a in h["abilities"] if a["cd"])
    n_tu = sum(len(h["teamups"]) for h in heroes)
    print(f"wrote site_data.json: {len(heroes)} heroes, {n_ab} abilities "
          f"({n_cd} quizzable cooldowns), {n_tu} team-ups")


if __name__ == "__main__":
    build()
