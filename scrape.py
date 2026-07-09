from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
HEROES_DIR = DATA / "heroes"
BASE = "https://www.marvelrivals.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Referer": "https://www.marvelrivals.com/heroes/index.html",
    "Accept-Language": "en-US,en;q=0.9",
}

session = requests.Session()
session.headers.update(HEADERS)


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).replace("​", "").strip()


def slug(s: str) -> str:
    s = clean(s).lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "x"


def get(url: str, tries: int = 4):
    err = None
    for i in range(tries):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            return r
        except Exception as e:
            err = e
            time.sleep(1.2 * (i + 1))
    raise err


def stat_pairs(cell) -> dict:
    out = {}
    for tr in cell.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) == 2:
            k = clean(tds[0].get_text())
            v = clean(tds[1].get_text())
            if k:
                out[k] = v
    return out


def imgs_in(cell) -> list[str]:
    return [urljoin(BASE, i.get("src")) for i in cell.find_all("img") if i.get("src")]


def parse_article(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    art = soup.select_one(".artText")

    def ptext(cls):
        el = art.select_one("." + cls)
        return clean(el.get_text()) if el else ""

    hero = {
        "name": ptext("p1"),
        "real_name": ptext("p2"),
        "role": ptext("p3"),
        "description": ptext("p4"),
        "lore": clean(art.select_one(".d1").get_text()) if art.select_one(".d1") else "",
        "base_stats": {},
        "portraits": [],
        "forms": [],
        "abilities": [],
        "team_ups": {"received": [], "provided": []},
    }

    main = soup.select_one(".table-imgs")
    anchors = [tr for tr in main.find_all("tr")
               if len(tr.find_all("td", recursive=False)) == 6]

    pending = None

    def flush():
        nonlocal pending
        if pending:
            hero["team_ups"]["provided"].append(pending)
            pending = None

    for tr in anchors:
        c = tr.find_all("td", recursive=False)
        cat = clean(c[0].get_text())
        name = clean(c[1].get_text())
        icon = c[2].find("img")
        icon = urljoin(BASE, icon.get("src")) if icon and icon.get("src") else None
        desc = clean(c[3].get_text())
        stats = stat_pairs(tr)

        if cat == "0":
            block_stats = stats or _kv_from_text(desc)
            block_imgs = imgs_in(c[4]) + imgs_in(c[5])
            hero["forms"].append({"name": name, "stats": block_stats, "images": block_imgs})
            if not hero["base_stats"]:
                hero["base_stats"] = block_stats
                hero["portraits"] = block_imgs
            continue

        if cat in ("1", "2"):
            key = stats.get("Key", "")
            slot = "primary" if cat == "1" else (
                "passive" if key.lower() == "passive" or "passive" in name.lower() else "ability")
            hero["abilities"].append({
                "name": name, "slot": slot, "key": key,
                "icon": icon, "description": desc, "stats": stats,
            })
            continue

        if cat == "3":
            hero["team_ups"]["received"].append({
                "name": name, "icon": icon, "description": desc, "stats": stats,
            })
            continue

        if cat == "4":
            if name == "占位空格" or (not desc and not stats):
                flush()
                continue
            base_txt, _, enh_txt = desc.partition("Enhanced Effect:")
            base_txt = clean(base_txt.replace("Base Effect:", ""))
            enh_txt = clean(enh_txt)
            partner = ""
            m = re.search(r"teaming up with ([^,.]+)", enh_txt, re.I)
            if m:
                partner = clean(m.group(1))
            if pending and pending["name"] == name and pending["enhanced"] is None:
                pending["enhanced"] = {"description": enh_txt, "stats": stats}
            else:
                flush()
                pending = {
                    "name": name, "icon": icon, "partner": partner,
                    "base": {"description": base_txt, "stats": stats},
                    "enhanced": None,
                }
    flush()
    for t in hero["team_ups"]["provided"]:
        if t["enhanced"] is None:
            t["enhanced"] = {"description": "", "stats": {}}
    return hero


def _kv_from_text(txt: str) -> dict:
    out = {}
    m = re.search(r"Health\s+([^A-Z]*?)\s+Movement Speed\s+(.+)", txt)
    if m:
        out["Health"] = clean(m.group(1))
        out["Movement Speed"] = clean(m.group(2))
    return out


def download(url: str, dest: Path, force: bool) -> bool:
    if dest.exists() and not force:
        return True
    try:
        r = get(url)
    except Exception as e:
        print(f"      ! image failed {url}: {e}", file=sys.stderr)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return True


def localize(url: str, dest: Path, force: bool, cache: dict) -> str | None:
    if not url:
        return None
    if url in cache:
        return cache[url]
    ok = download(url, dest, force)
    rel = str(dest.relative_to(HEROES_DIR).as_posix()) if ok else None
    cache[url] = rel
    return rel


def scrape_hero(name: str, uuid: str, path: str, force: bool) -> dict:
    url = BASE + path
    r = get(url)
    r.encoding = "utf-8"
    hero = parse_article(r.text)
    hero["source_name"] = name
    hero["uuid"] = uuid
    hero["article_url"] = url

    hslug = slug(name)
    hdir = HEROES_DIR / hslug
    cache: dict[str, str] = {}

    for i, u in enumerate(hero["portraits"], 1):
        hero.setdefault("portrait_files", []).append(
            localize(u, hdir / "portraits" / f"portrait_{i}.png", force, cache))

    for i, ab in enumerate(hero["abilities"], 1):
        fn = f"{i:02d}_{ab['slot']}_{slug(ab['key']) or 'x'}_{slug(ab['name'])}.png"
        ab["icon_file"] = localize(ab["icon"], hdir / "abilities" / fn, force, cache)

    for i, t in enumerate(hero["team_ups"]["received"], 1):
        fn = f"received_{i:02d}_{slug(t['name'])}.png"
        t["icon_file"] = localize(t["icon"], hdir / "teamups" / fn, force, cache)

    for i, t in enumerate(hero["team_ups"]["provided"], 1):
        fn = f"provided_{i:02d}_{slug(t['name'])}.png"
        t["icon_file"] = localize(t["icon"], hdir / "teamups" / fn, force, cache)

    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "data.json").write_text(
        json.dumps(hero, indent=2, ensure_ascii=False), encoding="utf-8")
    return hero


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="substring filter on hero name")
    ap.add_argument("--force", action="store_true", help="re-download existing images")
    ap.add_argument("--sleep", type=float, default=0.6)
    args = ap.parse_args()

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    HEROES_DIR.mkdir(parents=True, exist_ok=True)

    index = []
    for name, uuid, path in manifest:
        if args.only and args.only.lower() not in name.lower():
            continue
        try:
            hero = scrape_hero(name, uuid, path, args.force)
        except Exception as e:
            print(f"[FAIL] {name}: {e}", file=sys.stderr)
            continue
        na = len(hero["abilities"])
        nt = len(hero["team_ups"]["provided"]) + len(hero["team_ups"]["received"])
        print(f"[ok] {hero['name']:22} {hero['role']:12} "
              f"abilities={na:2} teamups={nt} portraits={len(hero['portraits'])}")
        index.append({
            "name": hero["name"], "slug": slug(name), "role": hero["role"],
            "uuid": uuid, "abilities": na,
            "team_ups": [t["name"] for t in hero["team_ups"]["provided"]],
            "dir": f"heroes/{slug(name)}",
        })
        time.sleep(args.sleep)

    if not args.only:
        (DATA / "index.json").write_text(
            json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {len(index)} heroes to {DATA/'index.json'}")


if __name__ == "__main__":
    main()
