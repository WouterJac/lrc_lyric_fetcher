# lrc_lyric_fetcher: Offline Lyrics Fetcher for Music Libraries

A fast, parallel, and polite tool to fetch LRC lyrics for your offline music library using the LRCLIB API. This tool supports album-level batching, failed-lookup caching, and per-album progress reporting, making it ideal for large music collections.
Coded with help from AI coding tools.

---

## Features

* ✅ Parallel fetching of lyrics for multiple tracks
* ✅ Album-level batching for better progress tracking
* ✅ Skips tracks that already have `.lrc` files or embedded lyrics
* ✅ Failed lookup caching to prevent repeated failed requests
* ✅ Per-track output and per-album progress reports
* ✅ Final summary report after completion
* ✅ Supports unsynced lyrics as a fallback

---

## Requirements

* Python 3.8 or higher
* Dependencies:

  * `mutagen` (for reading audio file metadata)
  * `requests` (for HTTP requests)
  * `tqdm` (for progress bars)

Install dependencies via pip:

```bash
pip install mutagen requests tqdm
```

---

## Installation

1. Download `lrc_lyric_fetcher.py` and place it in a convenient folder.
2. Ensure your music library is organized in folders (Artist/Album/Track).
3. Run the script from the terminal.

---

## Usage

```bash
python lrc_lyric_fetcher.py <music_folder> [options]
```

### Positional Arguments

* `<music_folder>` : Path to the root directory of your music library.

### Options

* `--overwrite` : Overwrite existing `.lrc` files (embedded lyrics are still skipped).
* `--unsynced`  : Allow unsynced/plain lyrics as a fallback.
* `--workers N` : Number of parallel worker threads (default: 5).

### Example

```bash
python lrc_lyric_fetcher.py ~/Music --workers 5 --unsynced
```

This will process your music library at `~/Music` using 5 parallel workers and allow unsynced lyrics as fallback.

---

## Caching

* Failed lookups are saved to `.failed_lyrics_cache.json` in the current directory.
* Subsequent runs will skip tracks that previously failed.
* Delete this file to retry failed tracks.

---

## Output

* `.lrc` files will be created alongside each track.
* Thread-safe per-track success/failure output is printed.
* After each album, a summary is printed:

```
📁 Finished album: Artist · Album
   → Success: 10 | Failed: 1 | Skipped: 1
```

* Final summary after the whole library:

```
===== LRC FETCH SUMMARY =====
Total tracks     : 1243
Downloaded LRCs  : 987
Failed lookups   : 41
Skipped tracks   : 215
Failure cache    : .failed_lyrics_cache.json
============================
```

---

## Notes / Recommendations

* Recommended worker count: 3–5 for small libraries, up to 8–10 for larger ones.
* Be polite: LRCLIB may throttle excessive parallel requests.
* Ensure your music files have proper metadata (`artist`, `title`, `album`) for best results.
* The script is idempotent and can be run multiple times safely.

---

## License

This project is free to use for personal purposes. Attribution is appreciated.

---

## Contact / Support

For issues or suggestions, please create an issue on the repository where you host the script.
