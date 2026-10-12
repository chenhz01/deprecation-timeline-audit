# -*- coding: utf-8 -*-
"""deprecation-timeline-audit: sunset-date extraction + expiry grading (stdlib).

Audits API deprecation declarations: extracts sunset dates (ISO or
"June 1, 2027" prose), grades urgency (expired / imminent / soon / ok),
checks date ordering, replacement presence, and grace-period consistency.
Pure stdlib, offline, deterministic given an explicit --today.
"""
import argparse
import datetime
import json
import re
import sys

__version__ = "0.1.1"

MONTHS = {name: i + 1 for i, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}

ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
PROSE_RE = re.compile(r"[A-Za-z]+\s+\d{1,2},?\s+\d{4}")
SUNSET_LINE_RE = re.compile(r"sunset", re.I)
OVERRIDE_RE = re.compile(r"")


def parse_date(s):
    """Parse ISO YYYY-MM-DD or 'Month D, YYYY'; return date or None."""
    if not isinstance(s, str):
        return None
    s = s.strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", s)
    if m and m.group(1).lower() in MONTHS:
        try:
            return datetime.date(int(m.group(3)), MONTHS[m.group(1).lower()],
                                 int(m.group(2)))
        except ValueError:
            return None
    return None


def extract_sunset_dates(text):
    """Scan text for lines mentioning 'sunset'; return [{line, date, raw}]."""
    if not isinstance(text, str):
        raise TypeError("text must be str")
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if not SUNSET_LINE_RE.search(line):
            continue
        for mt in ISO_RE.finditer(line):
            d = parse_date(mt.group(0))
            if d:
                out.append({"line": n, "date": d.isoformat(), "raw": mt.group(0)})
        for mt in PROSE_RE.finditer(line):
            d = parse_date(mt.group(0))
            if d:
                out.append({"line": n, "date": d.isoformat(), "raw": mt.group(0)})
    return out


def _is_bool(v):
    return isinstance(v, bool)


def audit_declarations(decls, today):
    """Audit a list of declaration dicts against `today` (a datetime.date).

    Returns findings; raises TypeError on non-list decls or non-date today.
    """
    if not isinstance(decls, list):
        raise TypeError("declarations must be a list")
    if not isinstance(today, datetime.date):
        raise TypeError("today must be a datetime.date")
    findings = []

    def add(code, sev, msg, loc):
        findings.append({"code": code, "severity": sev, "message": msg, "location": loc})

    for i, d in enumerate(decls):
        loc = "$.declarations[%d]" % i
        if not isinstance(d, dict):
            add("DECL_NOT_OBJECT", "ERROR", "declaration must be an object", loc)
            continue
        name = d.get("name")
        if not isinstance(name, str) or not name.strip():
            add("NAME_MISSING", "ERROR", "declaration requires non-empty 'name'", loc)
            name = "#%d" % i

        deprecated = d.get("deprecated", False)
        if not _is_bool(deprecated):
            add("DEPRECATED_NOT_BOOL", "WARN",
                "'deprecated' should be a boolean", loc)
            deprecated = bool(deprecated)

        sunset_raw = d.get("sunset_date")
        sunset = parse_date(sunset_raw) if sunset_raw is not None else None
        if deprecated and sunset_raw is None:
            add("SUNSET_MISSING", "ERROR",
                "deprecated API '%s' has no sunset_date" % name, loc)
        elif sunset_raw is not None and sunset is None:
            add("SUNSET_UNPARSEABLE", "ERROR",
                "sunset_date %r for '%s' is not a supported date format"
                % (sunset_raw, name), loc)

        dep_raw = d.get("deprecation_date")
        dep = parse_date(dep_raw) if dep_raw is not None else None
        if dep_raw is not None and dep is None:
            add("DEPRECATION_UNPARSEABLE", "ERROR",
                "deprecation_date %r for '%s' is not a supported date format"
                % (dep_raw, name), loc)

        if deprecated and sunset is not None:
            delta = (sunset - today).days
            if delta < 0:
                add("ALREADY_SUNSET", "ERROR",
                    "'%s' sunset %s is in the past (%d days)" % (name, sunset, -delta), loc)
            elif delta <= 30:
                add("SUNSET_IMMINENT", "ERROR",
                    "'%s' sunsets in %d days (%s)" % (name, delta, sunset), loc)
            elif delta <= 90:
                add("SUNSET_SOON", "WARN",
                    "'%s' sunsets in %d days (%s)" % (name, delta, sunset), loc)

        if (not deprecated) and sunset is not None and (sunset - today).days < 0:
            add("STALE_SUNSET_PAST", "WARN",
                "'%s' not deprecated but its sunset date has passed" % name, loc)

        if dep is not None and sunset is not None and dep > sunset:
            add("DATE_ORDER", "ERROR",
                "deprecation_date is after sunset_date for '%s'" % name, loc)

        if deprecated and not (isinstance(d.get("replacement"), str)
                               and d.get("replacement").strip()):
            add("NO_REPLACEMENT", "WARN",
                "deprecated API '%s' declares no replacement" % name, loc)

        grace = d.get("grace_period_days")
        if grace is not None:
            if not isinstance(grace, int) or isinstance(grace, bool) or grace < 0:
                add("GRACE_INVALID", "WARN",
                    "grace_period_days must be a non-negative integer", loc)
            elif dep is not None and sunset is not None and (sunset - dep).days < grace:
                add("GRACE_SHORT", "WARN",
                    "declared grace %d days exceeds deprecation-to-sunset span (%d days) for '%s'"
                    % (grace, (sunset - dep).days, name), loc)
    return findings


def summarize(findings):
    out = {"error": 0, "warn": 0, "info": 0}
    for f in findings:
        key = f["severity"].lower()
        out[key] = out.get(key, 0) + 1
    return out


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="deprecation-timeline-audit",
        description="Audit API deprecation timelines: extract sunset dates, "
                    "grade urgency, check replacement and grace periods.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("audit", help="audit a declarations JSON file")
    pa.add_argument("file", help="JSON: {\"declarations\": [...]} or [...]")
    pa.add_argument("--today", default=None,
                    help="reference date YYYY-MM-DD (default: system today)")
    pa.add_argument("--json", dest="as_json", action="store_true")

    ps = sub.add_parser("scan", help="extract sunset dates from a text file")
    ps.add_argument("file", help="text/markdown file to scan")
    ps.add_argument("--json", dest="as_json", action="store_true")

    a = p.parse_args(argv)

    try:
        with open(a.file, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print("error: cannot read file: %s" % e, file=sys.stderr)
        sys.exit(2)

    if a.cmd == "scan":
        hits = extract_sunset_dates(content)
        if a.as_json:
            print(json.dumps({"sunset_dates": hits}, ensure_ascii=False, indent=2))
        else:
            for h in hits:
                print("line %d: %s (raw: %s)" % (h["line"], h["date"], h["raw"]))
            print("found %d sunset date(s)" % len(hits))
        sys.exit(0)

    try:
        data = json.loads(content)
    except ValueError as e:
        print("error: declarations file is not valid JSON: %s" % e, file=sys.stderr)
        sys.exit(2)
    decls = data.get("declarations") if isinstance(data, dict) else data
    if not isinstance(decls, list):
        print("error: expected a list of declarations or {\"declarations\": [...]}",
              file=sys.stderr)
        sys.exit(2)

    today = datetime.date.today()
    if a.today:
        today = parse_date(a.today)
        if today is None:
            print("error: --today must be YYYY-MM-DD", file=sys.stderr)
            sys.exit(2)

    try:
        findings = audit_declarations(decls, today)
    except TypeError as e:
        print("error: %s" % e, file=sys.stderr)
        sys.exit(2)

    s = summarize(findings)
    if a.as_json:
        print(json.dumps({"findings": findings, "summary": s, "today": today.isoformat()},
                         ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print("[%s] %s %s: %s" % (f["severity"], f["location"],
                                      f["code"], f["message"]))
        print("summary: %d error(s), %d warn(s), %d info(s) (today=%s)"
              % (s["error"], s["warn"], s["info"], today.isoformat()))
    sys.exit(1 if s["error"] else 0)


if __name__ == "__main__":
    main()
