# Alignment Audit (Rules 85-100 / 16 items) — deprecation-timeline-audit

Audited: 2026-10-13 (round 2, v0.1.1).

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | 85 Safety/Ethics section | PASS | Defensive process tool, no offensive capability. README "Limits" covers threshold-gaming risk. No security-research content, so no separate Ethics section required. |
| 2 | 86 Privacy de-identification | PASS | Zero secrets/tokens/real names; endpoint names are placeholders (`GET /v1/thing`). Grep for `(sk-\|ghp_\|api_key=)` returns 0 hits. |
| 3 | 87 Copyright boundary | PASS | All content authored fresh; RFC 8594 referenced by name/number only. LICENSE (MIT, "zhengming contributors") present. |
| 4 | 88 Fact-check labeling | PASS | Performance numbers tagged [Measured] with repro command (timeit over audit_declarations). |
| 5 | 89 Confidence grading | PASS | README closing block: High (parsing/grading/consistency) / Medium (threshold fit) with justification. |
| 6 | 90 PLAN B built-in | PASS | README "Minimal Fallback": grep pipeline for date-less sunset mentions. |
| 7 | 91 Timeout presets | PASS | Quickstart marks ~2 min total, per-command ~0.5s, self-test ~0.5s. |
| 8 | 92 Rule-conflict arbitration | PASS | README "Design Trade-offs": missed-sunset detection > consistency > convenience; fixed thresholds justified. |
| 9 | 93 Version changelog | PASS | CHANGELOG.md has v0.1.0 and v0.1.1 with explicit iteration improvements. |
| 10 | 94 Exemption instruction | N/A | Session-governance rule; static repo content cannot carry exemptions. |
| 11 | 95 External-knowledge cutoff | PASS | README marks environment and "as of 2026-10-13" for landscape claims and measurements. |
| 12 | 96 Explicit assumptions | PASS | README `[Core Assumptions]` lists 4 premises. |
| 13 | 97 Logic-verification trio | PASS | self_test.py: 73 cases = functional A + CLI/exception B + extreme edges C (empty lists, unicode names, invalid calendars, scalar JSON). SUMMARY: PASS 73/73. |
| 14 | 98 Socratic question | PASS | FAQ "When NOT to use this tool?" (gateway-enforced sunsets; tiny deprecation volume). |
| 15 | 99 Pareto iteration | PASS | Two rounds traceable: v0.1.0 -> review -> v0.1.1 (+4 edge cases, fixture isolation fix). CHANGELOG + TestR2 class. |
| 16 | 100 Ultimate minimal entry | PASS | README opening paragraph is 56 words with a need-judgment ("otherwise skip it"). |

Repro for status column: `python self_test.py` -> `SUMMARY: PASS 73/73`.
