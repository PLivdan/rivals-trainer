# Marvel Rivals Hero Assets

**Live trainer:** https://plivdan.github.io/rivals-trainer/


Structured scrape of every hero's abilities, team-ups, base stats and **transparent
icon art** from the official Marvel Rivals "Hero Ability Data Dossier"
(`marvelrivals.com/heroes`). Data reflects the current live season.

## What it grabs

For all 52 heroes:

- Identity: display name, real name, role, tagline, lore.
- Base stats (health, movement speed, ...) and hero portraits/renders. Multi-form
  heroes (e.g. Black Cat) keep every form under `forms`.
- Every ability: input key, name, description, full stat table, and a **transparent
  PNG icon**. Slot is tagged `primary` / `ability` / `passive`.
- Every team-up:
  - `received` — team-ups the hero benefits from (an ally anchors it).
  - `provided` — team-ups the hero grants, each with its **base effect** and
    **enhanced effect** (stats for both) plus the partner hero parsed from the text
    ("When teaming up with Storm/Ultron ...").

## Layout

```
manifest.json                 hero -> official article URL (52 rows)
scrape.py                     the scraper
data/
  index.json                  roster summary
  heroes/<slug>/
    data.json                 full structured record (UTF-8)
    abilities/                NN_<slot>_<key>_<name>.png   (transparent)
    teamups/                  received_*.png / provided_*.png (transparent)
    portraits/                portrait_N.png (renders; may have backgrounds)
```

Example (`data/heroes/adam-warlock/`): 7 ability icons, team-ups Cosmic Cyclone
(partner Storm) and Flawless Design (partner Ultron) each with base+enhanced stats,
plus the received team-up Heavenly Harmony.

## data.json schema

```jsonc
{
  "name", "real_name", "role", "description", "lore",
  "uuid", "article_url",
  "base_stats": { "Health": "275", "Movement Speed": "6 m/s" },
  "portraits": [url...], "portrait_files": [rel_path...],
  "forms": [ { "name", "stats", "images": [url...] } ],
  "abilities": [
    { "name", "slot", "key", "description",
      "stats": { ... }, "icon": url, "icon_file": rel_path }
  ],
  "team_ups": {
    "received": [ { "name", "description", "stats", "icon", "icon_file" } ],
    "provided": [
      { "name", "partner", "icon", "icon_file",
        "base":     { "description", "stats" },
        "enhanced": { "description", "stats" } }
    ]
  }
}
```

`icon_file` / `portrait_file` paths are relative to `data/heroes/`.

## Trainer site (rough sketch)

`index.html` is a self-contained study/quiz app built on this data — a faster,
searchable alternative to the official dossier with drill modes:

- **Browse** — searchable, role-filtered roster; click a hero for abilities
  with color-coded stat chips (⟳ cooldown, ⚔ damage, ✚ healing, ⏱ duration) and
  team-ups (base/enhanced) that show the **partner's face icon** instead of text.
- **Cooldown Quiz** — multiple-choice on ability cooldowns, scoped to all / a
  role / one hero; score, streak, best; reveal teaches the ability on answer.
- **Team-Ups** — *Learn* lists every team-up; *Quiz* is fill-in-the-blank on the
  partner hero (partner name blanked out of the enhanced effect text).

Build the data file then serve (fetch needs http, not file://):

```
python build_site.py                    # -> site_data.json
python -m http.server 8731              # open http://localhost:8731/index.html
```

`build_site.py` also holds per-hero banner overrides (`BANNERS`) for heroes with
no standard portrait row (e.g. Deadpool). Deployable as-is to GitHub Pages.

## Re-running

```
python scrape.py                 # all heroes; skips already-downloaded images
python scrape.py --only "STORM"  # single hero
python scrape.py --force         # re-download every image
```

Refreshing for a new season: re-capture `manifest.json` if the roster changed
(hero article URLs come from the heroes page), then run `scrape.py`.

## Notes

- Icons are downloaded as-is from the CDN and are already transparent RGBA PNGs.
  Portraits are full-body renders and may carry a background.
- Deadpool's page carries three role builds (Vanguard/Duelist/Strategist), so his
  record legitimately holds ~69 ability entries; Black Cat carries two forms plus
  seasonal-event items. Every icon URL is unique — no duplicates.
