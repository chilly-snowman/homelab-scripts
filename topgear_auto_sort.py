#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import time

RAW_BASE = "/srv/media/raw"
TV_BASE = "/srv/media/tv/Top Gear (2002)"
JELLYFIN_URL = "http://localhost:8096"
JELLYFIN_API_KEY = "3ab326bae64942cea4abdf9ac3fa319b"

# Episode counts per season
SEASON_EPISODES = {
    1: 10, 2: 10, 3: 9,  4: 10, 5: 9,  6: 11,
    7: 10, 8: 10, 9: 10, 10: 10, 11: 6, 12: 8,
    13: 8, 14: 7, 15: 7, 16: 7,  17: 7, 18: 7,
    19: 7, 20: 7, 21: 7, 22: 7
}

def get_episode_range(season, disc):
    """Calculate episode range for a given season and disc.
    Each disc has 3 episodes except the last which takes the remainder."""
    total = SEASON_EPISODES.get(season, 0)
    start = ((disc - 1) * 3) + 1
    end = min(start + 2, total)
    return start, end

def format_ep_range(start, end):
    if start == end:
        return f"E{start:02d}"
    return f"E{start:02d}-E{end:02d}"

def jellyfin_scan():
    subprocess.run([
        "curl", "-s", "-X", "POST",
        f"{JELLYFIN_URL}/Library/Refresh",
        "-H", f"X-Emby-Token: {JELLYFIN_API_KEY}"
    ], capture_output=True)
    print("Triggered Jellyfin scan")

def process_folder(folder_name):
    """Process a SX_DX style folder."""
    match = re.match(r"S(\d+)_D(\d+)$", folder_name, re.IGNORECASE)
    if not match:
        return False

    season = int(match.group(1))
    disc = int(match.group(2))

    if season not in SEASON_EPISODES:
        print(f"Unknown season {season}, skipping")
        return False

    start, end = get_episode_range(season, disc)
    ep_range = format_ep_range(start, end)
    filename = f"Top Gear (2002) - S{season:02d}{ep_range}.mkv"
    season_dir = os.path.join(TV_BASE, f"Season {season:02d}")
    dst = os.path.join(season_dir, filename)
    src_dir = os.path.join(RAW_BASE, folder_name)

    # Find the mkv file
    files = [f for f in os.listdir(src_dir) if f.endswith(".mkv")]
    if len(files) != 1:
        print(f"Expected 1 mkv in {folder_name}, found {len(files)} — skipping")
        return False

    src = os.path.join(src_dir, files[0])
    os.makedirs(season_dir, exist_ok=True)

    print(f"Moving: {src}")
    print(f"    -> {dst}")
    shutil.move(src, dst)

    # Clean up empty folder
    try:
        os.rmdir(src_dir)
    except OSError:
        pass

    return True

def handle_flat_mkv(filename):
    """Handle a flat .mkv file dropped directly in raw with no folder wrapper."""
    print(f"\nDetected flat file: {filename}")
    print("No folder wrapper found — need season and disc number.")
    try:
        season = int(input("Enter season number: "))
        disc = int(input("Enter disc number: "))
    except ValueError:
        print("Invalid input, skipping.")
        return False

    folder_name = f"S{season}_D{disc}"
    folder_path = os.path.join(RAW_BASE, folder_name)
    src = os.path.join(RAW_BASE, filename)

    os.makedirs(folder_path, exist_ok=True)
    shutil.move(src, os.path.join(folder_path, filename))
    print(f"Wrapped into {folder_name}/")
    return process_folder(folder_name)

def main():
    print("Watching for Top Gear discs in raw...")
    processed = set()

    while True:
        try:
            entries = os.listdir(RAW_BASE)
            for entry in entries:
                if entry in processed:
                    continue
                full_path = os.path.join(RAW_BASE, entry)
                if re.match(r"S(\d+)_D(\d+)$", entry, re.IGNORECASE) and os.path.isdir(full_path):
                    time.sleep(5)
                    print(f"\nDetected: {entry}")
                    if process_folder(entry):
                        jellyfin_scan()
                        processed.add(entry)
                elif entry.endswith(".mkv") and os.path.isfile(full_path):
                    time.sleep(5)
                    if handle_flat_mkv(entry):
                        jellyfin_scan()
                        processed.add(entry)
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(10)

if __name__ == "__main__":
    main()