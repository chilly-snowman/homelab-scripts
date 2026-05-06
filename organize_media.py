#!/usr/bin/env python3
import os
import shutil

DRY_RUN = False  # Set to False to actually execute

TV_BASE = "/srv/media/tv"
MOVIE_BASE = "/srv/media/movies"

def log(action, src, dst=None):
    if dst:
        print(f"[{action}] {src}\n        -> {dst}")
    else:
        print(f"[{action}] {src}")

def rename(src, dst):
    log("RENAME", src, dst)
    if not DRY_RUN:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)

def delete(path):
    log("DELETE", path)
    if not DRY_RUN:
        os.remove(path)

def rmdir(path):
    if os.path.isdir(path) and not os.listdir(path):
        log("RMDIR ", path)
        if not DRY_RUN:
            os.rmdir(path)

# ─── MOVIES ───────────────────────────────────────────────────────────────────
# For each movie folder, rename the single .mkv inside to match the folder name
movie_fixes = {
    "A Christmas Story":                       "A Christmas Story (1983)",
    "Harry Potter and the Goblet of Fire":     "Harry Potter and the Goblet of Fire (2005)",
    "Harry Potter and the Prizoner of Azkaban":"Harry Potter and the Prisoner of Azkaban (2004)",
    "Anchorman 2 The Legend Continues (2013)": "Anchorman 2 - The Legend Continues (2013)",
    "Stranger Than Fiction":                   "Stranger Than Fiction (2006)",
    "The Taking of Pelham 123":                "The Taking of Pelham 123 (2009)",
    "Trading Places":                          "Trading Places (1983)",
}

print("=" * 60)
print("MOVIES")
print("=" * 60)

for folder in sorted(os.listdir(MOVIE_BASE)):
    folder_path = os.path.join(MOVIE_BASE, folder)
    if not os.path.isdir(folder_path):
        continue

    # Use corrected folder name if one exists
    correct_name = movie_fixes.get(folder, folder)
    correct_folder = os.path.join(MOVIE_BASE, correct_name)

    # Find the mkv inside
    files = [f for f in os.listdir(folder_path) if f.endswith(".mkv")]
    if len(files) != 1:
        print(f"[SKIP  ] {folder} — {len(files)} mkv files found, manual review needed")
        continue

    src_file = os.path.join(folder_path, files[0])
    dst_file = os.path.join(correct_folder, correct_name + ".mkv")

    if folder != correct_name:
        log("RENAME DIR", folder_path, correct_folder)
        if not DRY_RUN:
            os.rename(folder_path, correct_folder)
        src_file = os.path.join(correct_folder, files[0])

    if src_file != dst_file:
        rename(src_file, dst_file)

# ─── TV: TOP GEAR (filename/folder name mismatch) ─────────────────────────────
print("\n" + "=" * 60)
print("TV — TOP GEAR (filename consistency)")
print("=" * 60)

tg_base = os.path.join(TV_BASE, "Top Gear (2002)")
for season in sorted(os.listdir(tg_base)):
    season_path = os.path.join(tg_base, season)
    if not os.path.isdir(season_path):
        continue
    for fname in sorted(os.listdir(season_path)):
        if not fname.endswith(".mkv"):
            continue
        # Normalize "Top Gear - S0XE..." to "Top Gear (2002) - S0XE..."
        if fname.startswith("Top Gear (2002)"):
            continue  # already correct
        new_fname = fname.replace("Top Gear -", "Top Gear (2002) -", 1)
        src = os.path.join(season_path, fname)
        dst = os.path.join(season_path, new_fname)
        rename(src, dst)

# ─── TV: DISC-BASED SHOWS ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("TV — DISC-BASED RENAMING")
print("=" * 60)

# Each entry: show folder name -> season -> ordered list of (disc, filename, episode_num) or DELETE
disc_maps = {
    "Breaking Bad (2008)": {
        "Season 01": [
            ("Disc 01", "Breaking Bad- Season 1- Disc 1-C1_t00.mkv", "E01"),
            ("Disc 01", "Breaking Bad- Season 1- Disc 1-C1_t01.mkv", "E02"),
            ("Disc 01", "Breaking Bad- Season 1- Disc 1-C1_t02.mkv", "E03"),
            ("Disc 02", "Breaking Bad- Season 1- Disc 2-C1_t00.mkv", "E04"),
            ("Disc 02", "Breaking Bad- Season 1- Disc 2-C1_t01.mkv", "E05"),
            ("Disc 02", "Breaking Bad- Season 1- Disc 2-C1_t02.mkv", "E06"),
            ("Disc 03", "Breaking Bad- Season 1- Disc 3-F1_t00.mkv", "E07"),
            ("Disc 03", "Breaking Bad- Season 1- Disc 3-D1_t04.mkv", "DELETE"),
            ("Disc 03", "Breaking Bad- Season 1- Disc 3-B4_t15.mkv", "DELETE"),
        ]
    },
    "Game of Thrones (2011)": {
        "Season 01": [
            ("Disc 01", "B1_t00.mkv", "E01"),
            ("Disc 01", "D1_t01.mkv", "E02"),
            ("Disc 01", "E1_t03.mkv", "DELETE"),
            ("Disc 02", "A1_t00.mkv", "E03"),
            ("Disc 02", "C1_t01.mkv", "E04"),
            ("Disc 03", "A1_t00.mkv", "E05"),
            ("Disc 03", "C1_t01.mkv", "E06"),
            ("Disc 04", "A1_t00.mkv", "E07"),
            ("Disc 04", "C1_t01.mkv", "E08"),
            ("Disc 05", "A1_t00.mkv", "E09"),
            ("Disc 05", "C1_t01.mkv", "E10"),
        ]
    },
    "Better Call Saul (2015)": {
        "Season 01": [
            ("Disc 01", "Better Call Saul - Season 1 - Disc 1-D1_t00.mkv", "E01"),
            ("Disc 01", "Better Call Saul - Season 1 - Disc 1-D1_t01.mkv", "E02"),
            ("Disc 01", "Better Call Saul - Season 1 - Disc 1-D1_t02.mkv", "E03"),
            ("Disc 01", "Better Call Saul - Season 1 - Disc 1-D1_t03.mkv", "E04"),
            ("Disc 02", "Better Call Saul - Season 1 - Disc 2-D1_t00.mkv", "E05"),
            ("Disc 02", "Better Call Saul - Season 1 - Disc 2-D1_t01.mkv", "E06"),
            ("Disc 02", "Better Call Saul - Season 1 - Disc 2-D1_t02.mkv", "E07"),
            ("Disc 03", "Better Call Saul - Season 1 - Disc 3-D1_t00.mkv", "E08"),
            ("Disc 03", "Better Call Saul - Season 1 - Disc 3-D1_t01.mkv", "E09"),
            ("Disc 03", "Better Call Saul - Season 1 - Disc 3-D1_t02.mkv", "E10"),
        ]
    },
    "House (2007)": {
        "Season 01": [
            ("Disc 01", "C1_t00.mkv", "E01"),
            ("Disc 01", "D1_t01.mkv", "E02"),
            ("Disc 01", "E1_t02.mkv", "E03"),
            ("Disc 01", "F1_t03.mkv", "E04"),
            ("Disc 02", "C1_t00.mkv", "E05"),
            ("Disc 02", "D1_t01.mkv", "E06"),
            ("Disc 02", "E1_t02.mkv", "E07"),
            ("Disc 02", "F1_t03.mkv", "E08"),
            ("Disc 03", "C1_t00.mkv", "E09"),
            ("Disc 03", "D1_t01.mkv", "E10"),
            ("Disc 03", "E1_t02.mkv", "E11"),
            ("Disc 03", "F1_t03.mkv", "E12"),
            ("Disc 04", "C1_t00.mkv", "E13"),
            ("Disc 04", "D1_t01.mkv", "E14"),
            ("Disc 04", "E1_t02.mkv", "E15"),
            ("Disc 04", "F1_t03.mkv", "E16"),
            ("Disc 05", "C1_t00.mkv", "E17"),
            ("Disc 05", "D1_t01.mkv", "E18"),
            ("Disc 05", "E1_t02.mkv", "E19"),
            ("Disc 05", "F1_t03.mkv", "E20"),
            ("Disc 06", "C1_t00.mkv", "E21"),
            ("Disc 06", "D1_t01.mkv", "E22"),
        ]
    },
}

for show, seasons in disc_maps.items():
    show_path = os.path.join(TV_BASE, show)
    show_name = show.replace(show[-7:], "").strip()  # strip " (YEAR)"
    for season, episodes in seasons.items():
        season_num = season.replace("Season ", "S")
        season_path = os.path.join(show_path, season)
        for disc, filename, ep in episodes:
            src = os.path.join(season_path, disc, filename)
            if ep == "DELETE":
                delete(src)
            else:
                dst = os.path.join(season_path, f"{show_name} - {season_num}{ep}.mkv")
                rename(src, dst)
        # Clean up empty disc folders after moves
        for disc in set(d for d, _, _ in episodes):
            rmdir(os.path.join(season_path, disc))

print("\n" + "=" * 60)
print("DRY RUN COMPLETE — no files were modified" if DRY_RUN else "DONE")
print("=" * 60)
