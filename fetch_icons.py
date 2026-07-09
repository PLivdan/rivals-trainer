from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Referer": "https://www.marvelrivals.com/heroes/index.html"}

M = "https://www.marvelrivals.com/pc/gw/5da825b19a6a/heros/"
E = "https://r.res.easebar.com/pic/"

RAW = """
ef4511de M d21
03af29d0 E 20250912/fb42acc6-da42-472d-bf2d-d7efd4dff5b5
84b3b29a E 20260417/2c0db7d2-1232-44de-865b-4ce1a4f6b70e
fa01bc79 M d1
baa0fe39 E 20241205/7e34f06f-150f-4ad3-8c86-2c7c73e95493
4bb813d7 E 20250808/d4aa1ebb-46cb-4ae8-ac82-611ea004609c
b3e3bc0b M d24
5b5a8c7a E 20241205/0f7b7427-3ff1-42d4-a965-3f35d4f49b51
4b46591b E 20260612/36d48d33-8bd7-498a-a98c-ed23ea7f8895
043108d4 E 20251011/bdf306ae-a908-495c-abcd-be4472db6620
3ef6b679 E 20260116/e877384d-6fa4-47d6-b040-f7300c7d0367
d579e90a E 20260515/4153653e-1dfa-4780-8aa2-cc2881dad902
692c786c M d2
91b586e3 E 20260213/985677e8-fd80-47ed-96cc-8309404e71d0
011f4b5b E 20250408/8a48f02e-4525-42e9-b465-38e228aee7db
46e47f1b E 20251115/a8e9881e-cc5b-4b01-99db-d83a4ced5aca
f29f3cf1 M d3
e7e0573d M d27
7db8153e M d5
9471f35c M d19
f0ec2612 E 20250220/d9c2e23d-53e8-4115-9ce1-008d22c5aa2e
9cc13662 E 20250113/c63fb614-e16c-46ce-877d-43317debebd5
c90562b1 E 20241201/18ea989f-ba46-432d-93c3-87463215de53
ef114434 M d6
49e078be M d23
dc1d68ab E 20260708/e05b0e7d-e887-4742-b91b-27d73182abb1
c6011abe M d7
1077f07b M d18
dd9a323f M d12
2dffcc89 M d11
bbb138f7 E 20250131/e5b6506e-c783-4f2d-980d-83f167473b82
fccfe09c E 20250113/54cfc983-1e9d-45b5-9dcd-ff3228425347
7dc8b934 M d26
afbd915c M d20
3929765b M d10
f2521fc5 E 20250711/570fc7a9-f109-4048-a997-ee40f292034d
1c8d092c E 20241127/32976573-8ea6-401a-86bd-7931248cd94e
e1fb7cc4 M d8
deb6b426 E 20251212/f6f6bb5a-a093-467a-9e1b-a34915911967
1d3f08cf E 20260615/28983645-5be9-4faa-8d29-748420191077
feef5830 M d13
4ed51741 E 20241201/aae04d93-a3ac-49d8-a8c3-bb9ab47b2bd9
f052a66a M d16
93784596 M d17
77ad32c5 M d4
10bfa106 E 20250220/657d8eca-6d1f-4ad9-8c9a-99e1afac2a25
fcddbb53 M d22
dddc5632 E 20250531/1ff03b44-8874-4962-a87a-19f2871f1e92
fa12017d M d14
bff0c7c6 E 20260320/a365b954-636c-4b3a-8dce-b81898cbda72
7b26015b M d25
a9b308ab E 20241205/04d0322f-e929-4b81-81e9-4817a3f221e1
"""


def slug(s):
    s = re.sub(r"\s+", " ", s).lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def url_of(kind, tail):
    return (M + tail + ".png") if kind == "M" else (E + tail + ".png")


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    by8 = {u[:8]: (name, slug(name)) for name, u, _ in manifest}
    rows = [ln.split() for ln in RAW.strip().splitlines()]
    ok = 0
    for u8, kind, tail in rows:
        if u8 not in by8:
            print("!! no manifest match", u8)
            continue
        name, sl = by8[u8]
        dest = DATA / "heroes" / sl / "icon.png"
        if dest.exists():
            ok += 1
            continue
        r = requests.get(url_of(kind, tail), headers=H, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        ok += 1
        print(f"[icon] {name}")
        time.sleep(0.3)
    print(f"done: {ok}/{len(rows)} icons present")


if __name__ == "__main__":
    main()
