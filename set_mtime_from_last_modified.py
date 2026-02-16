#!/usr/bin/env python3
"""
Scan all .txt files under a root folder (default: `EFTA/`), extract an HTTP-style
"Last-Modified" header from each file, convert it to US/Eastern and set the
file's mtime/atime to that datetime.

Usage examples:
  python set_mtime_from_last_modified.py       # runs against EFTA/ and applies changes
  python set_mtime_from_last_modified.py --dry-run  # only shows what would change

Notes:
- Requires Python 3.9+ for zoneinfo. If zoneinfo isn't available, falls back to
  fixed -05:00 (EST) offset.
- The script tries to parse RFC-2822 style dates using email.utils.parsedate_to_datetime.
- By default the timestamp is set to the exact instant represented by the header
  (so timezone-aware). If you want the "wallclock" Eastern time to be used as
  the file's local displayed time regardless of the machine timezone, use
  --use-est-wallclock.
"""

from pathlib import Path
import re
import os
import sys
import argparse
from email.utils import parsedate_to_datetime
import datetime

# Try to get America/New_York timezone; fall back to fixed -05:00 if unavailable
try:
    from zoneinfo import ZoneInfo
    NY_TZ = ZoneInfo("America/New_York")
except Exception:
    NY_TZ = datetime.timezone(datetime.timedelta(hours=-5))

LM_RE = re.compile(r"(?mi)^Last-Modified:\s*(.+)$")


def extract_last_modified(text: str):
    m = LM_RE.search(text)
    return m.group(1).strip() if m else None


def parsed_datetime(value: str):
    # returns a timezone-aware datetime on success, or raises
    dt = parsedate_to_datetime(value)
    if dt is None:
        raise ValueError(f"Could not parse date: {value!r}")
    # parsedate_to_datetime may return naive datetimes for some inputs; assume UTC then
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def set_file_mtime(path: Path, dt: datetime.datetime, use_wallclock=False):
    """
    Set file mtime/atime. If use_wallclock is False, dt is treated as absolute (tz-aware)
    and converted to epoch seconds. If True, dt is converted to America/New_York,
    stripped of tzinfo, then interpreted as local time for the epoch calculation.
    """
    if use_wallclock:
        # convert to Eastern, drop tzinfo => naive wallclock
        dt_est = dt.astimezone(NY_TZ).replace(tzinfo=None)
        # interpret that naive time as local timezone
        local_tz = datetime.datetime.now().astimezone().tzinfo
        dt_localized = dt_est.replace(tzinfo=local_tz)
        ts = dt_localized.timestamp()
    else:
        # canonical: use the absolute instant represented by the datetime
        dt_canonical = dt.astimezone(NY_TZ)
        ts = dt_canonical.timestamp()

    os.utime(path, (ts, ts))
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).astimezone(NY_TZ)


def process_file(path: Path, apply: bool, use_wallclock: bool):
    try:
        text = path.read_text(errors='ignore')
    except Exception as e:
        print(f"Failed to read {path}: {e}")
        return
    lm = extract_last_modified(text)
    if not lm:
        print(f"No Last-Modified header: {path}")
        return
    try:
        dt = parsed_datetime(lm)
    except Exception as e:
        print(f"Failed to parse Last-Modified for {path}: {lm!r} ({e})")
        return

    dt_est = dt.astimezone(NY_TZ)
    if apply:
        try:
            new_dt = set_file_mtime(path, dt, use_wallclock=use_wallclock)
            print(f"Set: {path} -> {new_dt.isoformat()}")
        except Exception as e:
            print(f"Failed to set mtime for {path}: {e}")
    else:
        if use_wallclock:
            # show the wallclock time we'd set
            wallclock = dt.astimezone(NY_TZ).replace(tzinfo=None)
            print(f"Would set (wallclock): {path} -> {wallclock.isoformat()} [America/New_York]")
        else:
            print(f"Would set: {path} -> {dt_est.isoformat()} [America/New_York]")


def main(argv=None):
    p = argparse.ArgumentParser(description="Set file mtimes from Last-Modified headers inside text files")
    p.add_argument('--root', '-r', default='EFTA', help='Root folder to scan (default: EFTA)')
    p.add_argument('--ext', default='.txt', help='File extension to look for (default: .txt)')
    p.add_argument('--dry-run', action='store_true', help="Don't change files, only show what would be done")
    p.add_argument('--use-est-wallclock', action='store_true', help=('Interpret the Eastern time as a wallclock and set the file mtime so the file\n'
                                                                     ' displays that Eastern local time on the current machine (useful if\n'
                                                                     ' you want the file timestamp to match the EST time literally).'))
    args = p.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"Root not found: {root}")
        return 2

    files = list(root.rglob(f'*{args.ext}'))
    if not files:
        print(f"No files matching *{args.ext} under {root}")
        return 0

    for f in files:
        process_file(f, apply=not args.dry_run, use_wallclock=args.use_est_wallclock)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
