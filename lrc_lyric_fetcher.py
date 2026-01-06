#!/usr/bin/env python3

import argparse
import sys
import json
import threading
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from mutagen import File
from tqdm import tqdm

# -----------------------------
# Configuration
# -----------------------------

AUDIO_EXTS = {".mp3", ".flac", ".m4a", ".ogg", ".wav"}
LRCLIB_URL = "https://lrclib.net/api/search"
BLACKLIST = ["live", "remix", "edit", "karaoke", "instrumental"]

FAILED_CACHE_FILE = Path(".failed_lyrics_cache.json")

# -----------------------------
# Helpers
# -----------------------------

def find_audio_files(root: Path):
    return [
        p for p in root.rglob("*")
        if p.suffix.lower() in AUDIO_EXTS
    ]

def extract_metadata(path: Path):
    audio = File(path, easy=True)
    if not audio or not audio.info:
        return None

    return {
        "artist": audio.get("artist", [None])[0],
        "title": audio.get("title", [None])[0],
        "album": audio.get("album", ["Unknown Album"])[0],
        "duration": int(audio.info.length),
        "path": path,
    }

def should_skip_title(title: str) -> bool:
    t = title.lower()
    return any(word in t for word in BLACKLIST)

def has_embedded_lyrics(path: Path) -> bool:
    audio = File(path, easy=True)
    if not audio:
        return False
    lyrics = audio.get("lyrics")
    return bool(lyrics and lyrics[0].strip())

def has_existing_lyrics(path: Path, overwrite: bool) -> bool:
    if path.with_suffix(".lrc").exists() and not overwrite:
        return True
    if has_embedded_lyrics(path):
        return True
    return False

# -----------------------------
# Failed cache
# -----------------------------

def load_failed_cache():
    if FAILED_CACHE_FILE.exists():
        return set(tuple(x) for x in json.loads(FAILED_CACHE_FILE.read_text()))
    return set()

def save_failed_cache(cache):
    FAILED_CACHE_FILE.write_text(
        json.dumps(sorted(list(cache)), indent=2),
        encoding="utf-8"
    )

# -----------------------------
# LRCLIB
# -----------------------------

def fetch_lrc(artist, title, duration=None, allow_unsynced=False):
    params = {
        "artist_name": artist,
        "track_name": title,
    }
    if duration:
        params["duration"] = duration

    r = requests.get(LRCLIB_URL, params=params, timeout=15)
    r.raise_for_status()
    results = r.json()

    for entry in results:
        if entry.get("syncedLyrics"):
            return entry["syncedLyrics"]

    if allow_unsynced:
        for entry in results:
            if entry.get("plainLyrics"):
                return entry["plainLyrics"]

    return None

# -----------------------------
# Output (thread-safe)
# -----------------------------

print_lock = threading.Lock()

def log(msg):
    with print_lock:
        print(msg)

# -----------------------------
# Worker
# -----------------------------

def process_track(meta, overwrite, allow_unsynced, failed_cache, counters, album_counters):
    key = (meta["artist"], meta["title"])

    if key in failed_cache:
        counters["skipped"] += 1
        album_counters["skipped"] += 1
        return

    path = meta["path"]

    if should_skip_title(meta["title"]):
        counters["skipped"] += 1
        album_counters["skipped"] += 1
        return

    if has_existing_lyrics(path, overwrite):
        counters["skipped"] += 1
        album_counters["skipped"] += 1
        return

    try:
        lyrics = fetch_lrc(
            meta["artist"],
            meta["title"],
            meta["duration"],
            allow_unsynced
        )

        if lyrics:
            path.with_suffix(".lrc").write_text(lyrics, encoding="utf-8")
            counters["success"] += 1
            album_counters["success"] += 1
            log(f"✔ SUCCESS | {meta['artist']} · {meta['album']} · {meta['title']}")
        else:
            failed_cache.add(key)
            counters["failed"] += 1
            album_counters["failed"] += 1
            log(f"✖ FAILED  | {meta['artist']} · {meta['album']} · {meta['title']}")

    except Exception as e:
        failed_cache.add(key)
        counters["failed"] += 1
        album_counters["failed"] += 1
        log(f"✖ FAILED  | {meta['artist']} · {meta['album']} · {meta['title']} — {e}")

# -----------------------------
# Album batching
# -----------------------------

def group_by_album(metas):
    albums = defaultdict(list)
    for m in metas:
        albums[(m["artist"], m["album"])].append(m)
    return albums

def process_library(root, overwrite, allow_unsynced, workers):
    audio_files = find_audio_files(root)
    metas = [extract_metadata(p) for p in audio_files]
    metas = [m for m in metas if m and m["artist"] and m["title"]]

    albums = group_by_album(metas)
    failed_cache = load_failed_cache()

    counters = {
        "total": len(metas),
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }

    for (artist, album), tracks in tqdm(albums.items(), desc="Albums", unit="album"):
        album_counters = {"success": 0, "failed": 0, "skipped": 0}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    process_track,
                    meta,
                    overwrite,
                    allow_unsynced,
                    failed_cache,
                    counters,
                    album_counters
                )
                for meta in tracks
            ]
            for _ in as_completed(futures):
                pass

        # Album-level progress report
        log(
            f"\n📁 Finished album: {artist} · {album}\n"
            f"   → Success: {album_counters['success']} | "
            f"Failed: {album_counters['failed']} | "
            f"Skipped: {album_counters['skipped']}\n"
        )

    save_failed_cache(failed_cache)
    return counters

# -----------------------------
# CLI
# -----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fast parallel LRC fetcher with caching and album batching (LRCLIB)"
    )

    parser.add_argument("path", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--unsynced", action="store_true")
    parser.add_argument("--workers", type=int, default=5)

    args = parser.parse_args()

    if not args.path.exists():
        print("Path does not exist", file=sys.stderr)
        sys.exit(1)

    counters = process_library(
        root=args.path,
        overwrite=args.overwrite,
        allow_unsynced=args.unsynced,
        workers=args.workers,
    )

    print("\n===== LRC FETCH SUMMARY =====")
    print(f"Total tracks     : {counters['total']}")
    print(f"Downloaded LRCs  : {counters['success']}")
    print(f"Failed lookups   : {counters['failed']}")
    print(f"Skipped tracks  : {counters['skipped']}")
    print(f"Failure cache   : {FAILED_CACHE_FILE}")
    print("============================")

if __name__ == "__main__":
    main()
