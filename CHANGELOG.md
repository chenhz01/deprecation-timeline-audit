# Changelog

## v0.1.1 (2026-10-13)

Round-2 revision after full self-review of the v0.1.0 draft:

- Added 4 extreme-edge test cases (1-day-to-sunset imminent grading, prose
  dates without commas, empty-string replacement warning, uppercase SUNSET
  keyword scanning); suite grew 69 -> 73 cases, all PASS.
- Fixed one round-2 fixture (grace period disabled on the imminent-sunset
  case so the assertion isolates a single finding).
- Measured and documented Performance numbers ([Measured] tags, repro
  commands).
- Added ALIGNMENT.md (rules 85-100 audit, 16 items with evidence).

## v0.1.0 (2026-10-13)

Initial draft:

- Date parsing: ISO YYYY-MM-DD plus prose "Month D, YYYY" (case-insensitive,
  comma-optional); invalid calendar dates rejected; leap days handled.
- Urgency grading against a reference date: ALREADY_SUNSET (error),
  SUNSET_IMMINENT <= 30 days (error), SUNSET_SOON <= 90 days (warn).
- Consistency rules: SUNSET_MISSING (deprecated without sunset), DATE_ORDER,
  NO_REPLACEMENT, GRACE_SHORT, GRACE_INVALID, STALE_SUNSET_PAST,
  DEPRECATED_NOT_BOOL, SUNSET_UNPARSEABLE / DEPRECATION_UNPARSEABLE.
- Text scan mode: `sunset:` mentions with line numbers and parsed dates.
- CLI (`audit`, `scan`, `--today`, `--json`) with exit-code contract 0/1/2.
- Self-test suite: 69 cases across functional / exception / extreme-edge
  classes, `SUMMARY: PASS n/n` reporting, four-defence template.
- README, MIT LICENSE.
