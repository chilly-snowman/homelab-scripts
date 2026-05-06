#!/usr/bin/env python3
import os
import shutil

DRY_RUN = False

RAW_BASE = "/srv/media/raw"
TV_BASE = "/srv/media/tv"

def log(action, src, dst=None):
    if dst:
        print(f"[{action}] {src}\n        -> {dst}")
    else:
        print(f"[{action}] {src}")

def rename(src, dst):
    log("MOVE", src, dst)
    if not DRY_RUN:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)

def rmdir(path):
    if os.path.isdir(path) and not os.listdir(path):
        log("RMDIR", path)
        if not DRY_RUN:
            os.rmdir(path)

disc_maps = {
    "Brooklyn Nine-Nine (2014)": {
        "Season 01": [
            ("Disc 01", "D1_t04.mkv", "E01"),
            ("Disc 01", "D2_t05.mkv", "E02"),
            ("Disc 01", "D4_t06.mkv", "E03"),
            ("Disc 01", "D5_t07.mkv", "E04"),
            ("Disc 01", "G1_t08.mkv", "E05"),
            ("Disc 01", "G2_t09.mkv", "E06"),
            ("Disc 01", "G4_t10.mkv", "E07"),
            ("Disc 01", "G6_t11.mkv", "E08"),
            ("Disc 02", "D1_t01.mkv", "E09"),
            ("Disc 02", "D3_t02.mkv", "E10"),
            ("Disc 02", "D4_t03.mkv", "E11"),
            ("Disc 02", "D6_t04.mkv", "E12"),
            ("Disc 02", "F1_t05.mkv", "E13"),
            ("Disc 02", "F3_t06.mkv", "E14"),
            ("Disc 02", "F5_t07.mkv", "E15"),
            ("Disc 03", "D1_t01.mkv", "E16"),
            ("Disc 03", "D3_t02.mkv", "E17"),
            ("Disc 03", "D5_t03.mkv", "E18"),
            ("Disc 03", "D7_t04.mkv", "E19"),
            ("Disc 03", "F1_t05.mkv", "E20"),
            ("Disc 03", "F3_t06.mkv", "E21"),
            ("Disc 03", "F5_t07.mkv", "E22"),
        ]
    },
    "Psych (2007)": {
        "Season 01": [
            ("Disc 01", "B1_t00.mkv", "E01"),
            ("Disc 01", "E3_t08.mkv", "E02"),
            ("Disc 02", "C1_t00.mkv", "E03"),
            ("Disc 02", "C2_t01.mkv", "E04"),
            ("Disc 02", "C3_t02.mkv", "E05"),
            ("Disc 02", "C4_t04.mkv", "E06"),
            ("Disc 02", "C5_t06.mkv", "E07"),
            ("Disc 03", "C1_t00.mkv", "E08"),
            ("Disc 03", "C2_t01.mkv", "E09"),
            ("Disc 03", "C3_t02.mkv", "E10"),
            ("Disc 03", "B1_t04.mkv", "E11"),
            ("Disc 03", "C4_t06.mkv", "E12"),
            ("Disc 04", "C1_t00.mkv", "E13"),
            ("Disc 04", "C2_t01.mkv", "E14"),
            ("Disc 04", "C3_t02.mkv", "E15"),
            ("Disc 04", "C4_t05.mkv", "E16"),
        ]
    },
}

for show, seasons in disc_maps.items():
    show_name = show.rsplit(" (", 1)[0]
    print("\n" + "=" * 60)
    print(show)
    print("=" * 60)
    for season, episodes in seasons.items():
        season_num = season.replace("Season ", "S")
        raw_season = os.path.join(RAW_BASE, show, season)
        dst_season = os.path.join(TV_BASE, show, season)
        for disc, filename, ep in episodes:
            src = os.path.join(raw_season, disc, filename)
            dst = os.path.join(dst_season, f"{show_name} - {season_num}{ep}.mkv")
            rename(src, dst)
        for disc in set(d for d, _, _ in episodes):
            rmdir(os.path.join(raw_season, disc))
        rmdir(raw_season)
    rmdir(os.path.join(RAW_BASE, show))

print("\n" + "=" * 60)
print("DRY RUN COMPLETE — no files modified" if DRY_RUN else "DONE")
print("=" * 60)
