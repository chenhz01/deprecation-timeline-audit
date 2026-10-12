# -*- coding: utf-8 -*-
"""self_test for deprecation-timeline-audit — R14, inherits 4-defence template v2."""
import atexit
import contextlib
import datetime
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deprecation_timeline_audit as m  # noqa: E402

_TMP = tempfile.mkdtemp(prefix="dta_selftest_")
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)
TODAY = datetime.date(2026, 10, 13)


def wf(name, content):
    p = os.path.join(_TMP, name)
    with open(p, "w", encoding="utf-8", newline="") as f:  # Defence 3
        f.write(content)
    return p


def run_cli(argv):
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            m.main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:  # noqa: BLE001
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


def decl(**kw):
    d = {"name": "GET /v1/thing", "deprecated": True, "deprecation_date": "2026-08-01",
         "sunset_date": "2027-06-01", "grace_period_days": 90, "replacement": "/v2/thing"}
    d.update(kw)
    return {k: v for k, v in d.items() if v is not None}


DECLS_OK = wf("b_ok.json", json.dumps({"declarations": [decl()]}))
DECLS_EXPIRED = wf("b_expired.json", json.dumps([decl(sunset_date="2026-09-30")]))
DECLS_MALFORMED = wf("b_malformed.json", "{oops")
SCAN_TXT = wf("scan.txt", "The v1 endpoint will sunset: 2027-01-15 per policy.\n"
                          "Sunset: February 1, 2028 for the legacy API.\n"
                          "No date here.\n")

# ---- [A] functional: (name, decls, checks, no_errors) ----
A_CASES = [
    ("valid_decl_clean", [decl()], [], True),
    ("sunset_missing", [decl(sunset_date=None)], [("SUNSET_MISSING", "")], False),
    ("sunset_past", [decl(sunset_date="2026-09-30")], [("ALREADY_SUNSET", "")], False),
    ("sunset_imminent_30d", [decl(sunset_date="2026-11-05")], [("SUNSET_IMMINENT", "")], False),
    ("sunset_soon_73d", [decl(sunset_date="2026-12-25")], [("SUNSET_SOON", "")], False),
    ("sunset_far_ok", [decl(sunset_date="2027-06-01")], [], True),
    ("sunset_today_imminent", [decl(sunset_date="2026-10-13")], [("SUNSET_IMMINENT", "")], False),
    ("sunset_yesterday_expired", [decl(sunset_date="2026-10-12")], [("ALREADY_SUNSET", "")], False),
    ("date_order", [decl(sunset_date="2026-07-01")], [("DATE_ORDER", "")], False),
    ("no_replacement", [decl(replacement=None)], [("NO_REPLACEMENT", "")], False),
    ("grace_short", [decl(deprecation_date="2026-10-01", sunset_date="2026-11-01")],
     [("GRACE_SHORT", "")], False),
    ("grace_ok", [decl(deprecation_date="2026-01-01", sunset_date="2026-12-01")], [], True),
    ("not_deprecated_sunset_past", [decl(deprecated=False, sunset_date="2026-01-01")],
     [("STALE_SUNSET_PAST", "")], False),
    ("not_deprecated_sunset_future_ok", [decl(deprecated=False, sunset_date="2027-06-01")], [], True),
    ("name_missing", [decl(name=None)], [("NAME_MISSING", "")], False),
    ("prose_date_parses", [decl(sunset_date="June 1, 2027")], [], True),
    ("sunset_unparseable", [decl(sunset_date="sometime soon")], [("SUNSET_UNPARSEABLE", "")], False),
    ("deprecation_unparseable", [decl(deprecation_date="last summer")],
     [("DEPRECATION_UNPARSEABLE", "")], False),
    ("deprecated_not_bool", [decl(deprecated="yes")], [("DEPRECATED_NOT_BOOL", "")], False),
    ("grace_negative", [decl(grace_period_days=-5)], [("GRACE_INVALID", "")], False),
    ("grace_bool", [decl(grace_period_days=True)], [("GRACE_INVALID", "")], False),
    ("delta_31_is_soon", [decl(sunset_date="2026-11-13")], [("SUNSET_SOON", "")], False),
    ("delta_91_is_ok", [decl(sunset_date="2027-01-12")], [], True),
    ("expired_by_1_day", [decl(sunset_date="2026-10-12")], [("ALREADY_SUNSET", "1 days")], False),
]


def _mk_a(name, decls, checks, no_errors):
    def t(self):
        fs = m.audit_declarations(decls, TODAY)
        if no_errors:
            self.assertEqual([f for f in fs if f["severity"] == "ERROR"], [], msg=name)
        for code, sub in checks:
            hit = [f for f in fs if f["code"] == code and sub in f["message"]]
            self.assertTrue(hit, msg="%s expects %s (%r)" % (name, code, sub))
    t.__doc__ = "A: %s" % name
    return t


class TestA(unittest.TestCase):
    def test_a24_prose_month_case_insensitive(self):
        self.assertEqual(m.parse_date("FEBRUARY 1, 2028").isoformat(), "2028-02-01")

    def test_a25_scan_extracts_two(self):
        hits = m.extract_sunset_dates(open(SCAN_TXT, encoding="utf-8").read())
        self.assertEqual([h["date"] for h in hits], ["2027-01-15", "2028-02-01"])

    def test_a26_scan_lines_are_1_based(self):
        hits = m.extract_sunset_dates("hello\nsunset: 2027-01-15\n")
        self.assertEqual(hits[0]["line"], 2)

    def test_a27_missing_severity_is_error(self):
        fs = m.audit_declarations([decl(sunset_date=None)], TODAY)
        self.assertEqual(fs[0]["severity"], "ERROR")

    def test_a28_leap_day_valid(self):
        self.assertEqual(m.parse_date("2024-02-29").isoformat(), "2024-02-29")

    def test_a29_non_list_raises(self):
        with self.assertRaises(TypeError):
            m.audit_declarations({"x": 1}, TODAY)


for _i, (_nm, _dl, _ck, _ne) in enumerate(A_CASES):
    setattr(TestA, "test_a%02d_%s" % (_i, _nm), _mk_a(_nm, _dl, _ck, _ne))

# ---- [B] CLI contract ----
B_CASES = [
    ("audit_valid_exit0", ["audit", DECLS_OK], 0, "", ""),
    ("audit_expired_exit1", ["audit", DECLS_EXPIRED], 1, "", ""),
    ("audit_json_flag", ["audit", DECLS_OK, "--json"], 0, '"findings"', ""),
    ("audit_malformed_json", ["audit", DECLS_MALFORMED], 2, "", "not valid JSON"),
    ("audit_missing_file", ["audit", "absent_decls.json"], 2, "", "cannot read"),
    ("audit_today_override_ok", ["audit", DECLS_EXPIRED, "--today", "2026-01-01"], 0, "", ""),
    ("audit_today_invalid", ["audit", DECLS_OK, "--today", "not-a-date"], 2, "", "YYYY-MM-DD"),
    ("scan_extracts", ["scan", SCAN_TXT], 0, "2027-01-15", ""),
    ("scan_json", ["scan", SCAN_TXT, "--json"], 0, '"sunset_dates"', ""),
    ("scan_no_dates", ["scan", wf("nodates.txt", "nothing here\n")], 0, "found 0", ""),
    ("scan_missing_file", ["scan", "absent.txt"], 2, "", "cannot read"),
]


def _mk_b(name, argv, code, out_sub="", err_sub=""):
    def t(self):
        c, out, err = run_cli(argv)
        self.assertEqual(c, code, msg="out=%r err=%r" % (out, err))
        if out_sub:
            self.assertIn(out_sub, out)
        if err_sub:
            self.assertIn(err_sub, err)
    t.__doc__ = "B: %s" % name
    return t


class TestB(unittest.TestCase):
    def test_b11_no_subcommand_exit2(self):
        c, _out, _err = run_cli([])
        self.assertEqual(c, 2)

    def test_b12_help_exit0(self):
        c, out, _err = run_cli(["--help"])
        self.assertEqual(c, 0)
        self.assertIn("usage:", out)

    def test_b13_audit_summary_line(self):
        c, out, _err = run_cli(["audit", DECLS_OK])
        self.assertEqual(c, 0)
        self.assertIn("summary:", out)


for _i, (_nm, _av, _cd, _os, _es) in enumerate(B_CASES):
    setattr(TestB, "test_b%02d_%s" % (_i, _nm), _mk_b(_nm, _av, _cd, _os, _es))

# ---- [C] extreme/edge ----
C_CASES = [
    ("empty_decls_list", lambda s: s.assertEqual(m.audit_declarations([], TODAY), [])),
    ("decl_not_object", lambda s: s.assertTrue(any(
        f["code"] == "DECL_NOT_OBJECT" for f in m.audit_declarations([42], TODAY)))),
    ("decls_none_raises", lambda s: s.assertRaises(TypeError, m.audit_declarations, None, TODAY)),
    ("today_not_date_raises", lambda s: s.assertRaises(TypeError, m.audit_declarations, [decl()], "2026-10-13")),
    ("parse_none", lambda s: s.assertIsNone(m.parse_date(None))),
    ("parse_int", lambda s: s.assertIsNone(m.parse_date(20261013))),
    ("parse_invalid_month", lambda s: s.assertIsNone(m.parse_date("Foo 1, 2027"))),
    ("parse_invalid_day", lambda s: s.assertIsNone(m.parse_date("2026-02-30"))),
    ("parse_iso_only", lambda s: s.assertIsNone(m.parse_date("2026/10/13"))),
    ("unicode_name_ok", lambda s: s.assertEqual(
        [f for f in m.audit_declarations([decl(name="接口 /v1/旧")], TODAY)
         if f["severity"] == "ERROR"], [])),
    ("scan_empty_text", lambda s: s.assertEqual(m.extract_sunset_dates(""), [])),
    ("scan_no_sunset_keyword", lambda s: s.assertEqual(
        m.extract_sunset_dates("2027-01-15 without the word\n"), [])),
    ("scan_multiple_dates_one_line", lambda s: s.assertEqual(
        len(m.extract_sunset_dates("sunset 2027-01-15 and 2028-02-01")), 2)),
    ("scan_none_raises", lambda s: s.assertRaises(TypeError, m.extract_sunset_dates, None)),
    ("scan_prose_uppercase_month", lambda s: s.assertEqual(
        m.extract_sunset_dates("Sunset: JUNE 1, 2027")[0]["date"], "2027-06-01")),
    ("scan_ignores_non_dates", lambda s: s.assertEqual(
        m.extract_sunset_dates("sunset policy has no date"), [])),
    ("grace_none_ok", lambda s: s.assertEqual(
        [f for f in m.audit_declarations([decl(grace_period_days=None)], TODAY)
         if f["severity"] == "ERROR"], [])),
    ("grace_string_invalid", lambda s: s.assertTrue(any(
        f["code"] == "GRACE_INVALID" for f in m.audit_declarations(
            [decl(grace_period_days="90")], TODAY)))),
    ("grace_exactly_equal_span_ok", lambda s: s.assertEqual(
        [f for f in m.audit_declarations(
            [decl(deprecation_date="2026-08-01", sunset_date="2026-10-30",
                  grace_period_days=90)], TODAY)
         if f["code"] == "GRACE_SHORT"], [])),
    ("hundred_decls_completes", lambda s: s.assertEqual(
        len(m.audit_declarations([decl(name="API %d" % i) for i in range(100)], TODAY)), 0)),
    ("cli_json_roundtrip", lambda s: s.assertEqual(
        json.loads(run_cli(["audit", DECLS_OK, "--json"])[1])["summary"]["error"], 0)),
    ("cli_decls_list_format_ok", lambda s: s.assertEqual(
        run_cli(["audit", wf("c_list.json", json.dumps([decl()])), "--today", "2026-01-01"])[0], 0)),
    ("cli_decls_scalar_exit2", lambda s: s.assertEqual(
        run_cli(["audit", wf("c_scalar.json", json.dumps(42))])[0], 2)),
    ("cli_directory_exit2", lambda s: s.assertEqual(run_cli(["audit", _TMP])[0], 2)),
    ("emoji_name_no_crash", lambda s: s.assertIsInstance(
        m.audit_declarations([decl(name="🚀 /v1/x")], TODAY), list)),
]


class TestC(unittest.TestCase):
    pass


for _i, (_nm, _fn) in enumerate(C_CASES):
    setattr(TestC, "test_c%02d_%s" % (_i, _nm), _fn)


# ---- Round-2 additions (v0.1.1): extra extreme-edge coverage ----
class TestR2(unittest.TestCase):
    def test_r2_delta_1_imminent(self):
        fs = m.audit_declarations([decl(sunset_date="2026-10-14", grace_period_days=None)], TODAY)
        self.assertEqual([f["code"] for f in fs], ["SUNSET_IMMINENT"])

    def test_r2_prose_without_comma(self):
        self.assertEqual(m.parse_date("June 1 2027").isoformat(), "2027-06-01")

    def test_r2_empty_replacement_warns(self):
        fs = m.audit_declarations([decl(replacement="")], TODAY)
        self.assertTrue(any(f["code"] == "NO_REPLACEMENT" for f in fs))

    def test_r2_uppercase_sunset_keyword_scan(self):
        self.assertEqual(len(m.extract_sunset_dates("SUNSET: 2027-01-15")), 1)

if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))  # Defence 4
    sys.exit(0 if fails == 0 else 1)
