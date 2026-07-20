#!/usr/bin/env python3
"""Tests for the repo-scan ledger (scripts/repo_scan.py) behind /praxis:scan.

The ledger is the scanner's coverage guarantee, so these tests pin the parts
that make laziness impossible: full-inventory sharding, per-dimension audit
tracking, the finding lifecycle, and the INCOMPLETE flag in the report.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugins" / "praxis"
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS / "lib"))
sys.path.insert(0, str(SCRIPTS))
import common  # noqa: E402
import repo_scan  # noqa: E402


def run_scan(root, *args):
    """Invoke repo_scan.py as the model does, rooted at `root`."""
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "repo_scan.py"), *args],
        capture_output=True, text=True, env=env,
    )


class RepoScanBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        # A small non-git project: two subsystems plus root files.
        (self.root / "src").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "src" / "app.py").write_text("print('a')\n" * 10)
        (self.root / "src" / "util.py").write_text("print('u')\n" * 5)
        (self.root / "docs" / "index.md").write_text("# docs\n")
        (self.root / "README.md").write_text("# readme\n")

    def state(self):
        f = self.root / ".claude" / ".praxis" / "repo_scan.json"
        return json.loads(f.read_text()) if f.exists() else {}


class TestInventoryAndShards(RepoScanBase):
    def test_init_covers_every_kept_file_exactly_once(self):
        out = run_scan(self.root, "init")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        shards = self.state()["shards"]
        sharded = [f for sh in shards for f in sh["files"]]
        self.assertEqual(sorted(sharded), sorted(set(sharded)))
        self.assertEqual(
            sorted(sharded),
            sorted(["README.md", "docs/index.md", "src/app.py", "src/util.py"]))

    def test_init_excludes_noise_with_counts(self):
        (self.root / "logo.png").write_bytes(b"\x89PNG....")
        (self.root / "package-lock.json").write_text("{}")
        (self.root / "blob").write_bytes(b"\x00" * 100)          # binary sniff
        (self.root / "big.sql").write_text("x" * 600_000)         # oversize
        out = run_scan(self.root, "init")
        self.assertEqual(out.returncode, 0)
        excluded = self.state()["excluded"]
        self.assertEqual(excluded.get("binary"), 2)
        self.assertEqual(excluded.get("lockfile"), 1)
        self.assertEqual(excluded.get("oversize"), 1)

    def test_init_refuses_to_clobber_without_force(self):
        self.assertEqual(run_scan(self.root, "init").returncode, 0)
        self.assertEqual(run_scan(self.root, "init").returncode, 1)
        self.assertEqual(run_scan(self.root, "init", "--force").returncode, 0)

    def test_scope_filters_inventory(self):
        out = run_scan(self.root, "init", "--scope", "src")
        self.assertEqual(out.returncode, 0)
        files = [f for sh in self.state()["shards"] for f in sh["files"]]
        self.assertEqual(sorted(files), ["src/app.py", "src/util.py"])

    def test_shard_file_cap_splits_groups(self):
        for i in range(7):
            (self.root / "src" / f"m{i}.py").write_text("pass\n")
        run_scan(self.root, "init", "--shard-files", "3")
        src_shards = [sh for sh in self.state()["shards"] if sh["group"] == "src"]
        self.assertGreater(len(src_shards), 1)
        self.assertTrue(all(len(sh["files"]) <= 3 for sh in src_shards))

    def test_empty_scope_fails_cleanly(self):
        out = run_scan(self.root, "init", "--scope", "nonexistent")
        self.assertEqual(out.returncode, 1)
        self.assertIn("no auditable files", out.stdout)

    def test_skip_reason_flags_vendored_and_meta_paths(self):
        self.assertEqual(repo_scan._skip_reason("vendor/lib.js", self.root), "vendored")
        self.assertEqual(repo_scan._skip_reason(".claude/settings.json", self.root), "meta")

    def test_skip_reason_excludes_special_files(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("no mkfifo on this platform")
        os.mkfifo(self.root / "pipe.log")
        self.assertEqual(repo_scan._skip_reason("pipe.log", self.root), "special")

    def test_init_refuses_silent_truncation_above_max_files(self):
        out = run_scan(self.root, "init", "--max-files", "3")  # repo has 4 files
        self.assertEqual(out.returncode, 1)
        self.assertIn("refusing", out.stdout)
        self.assertEqual(self.state(), {})  # nothing half-built
        self.assertEqual(run_scan(self.root, "init", "--max-files", "4").returncode, 0)

    def test_scope_is_normalised_in_state(self):
        run_scan(self.root, "init", "--scope", "src/")
        self.assertEqual(self.state()["scope"], "src")

    def test_dot_slash_scope_normalises_and_scans(self):
        out = run_scan(self.root, "init", "--scope", "./src")
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertEqual(self.state()["scope"], "src")
        files = [f for sh in self.state()["shards"] for f in sh["files"]]
        self.assertEqual(sorted(files), ["src/app.py", "src/util.py"])

    def test_scope_escaping_the_repo_is_rejected(self):
        for scope in ("..", "../other", "/etc"):
            out = run_scan(self.root, "init", "--scope", scope)
            self.assertEqual(out.returncode, 1, scope)
            self.assertIn("inside the repo", out.stdout)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_git_mode_uses_index_and_pathspec_scope(self):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root))
        subprocess.run(["git", "init", "-q"], cwd=self.root, env=env, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.root, env=env, check=True)
        (self.root / "src" / "untracked.py").write_text("x")  # not staged
        out = run_scan(self.root, "init", "--scope", "./src")
        self.assertEqual(out.returncode, 0, out.stdout)
        files = [f for sh in self.state()["shards"] for f in sh["files"]]
        self.assertEqual(sorted(files), ["src/app.py", "src/util.py"])

    def test_dir_cap_hit_refuses_instead_of_truncating(self):
        with mock.patch.object(common, "walk_files", return_value=(["a.py"], True)):
            kept, excluded, overflow = repo_scan._inventory(self.root, ".", 100)
        self.assertEqual(overflow, "dirs")
        out_files, hit = common.walk_files(self.root, max_dirs=2)  # real cap check
        self.assertTrue(hit)

    def test_hand_edited_finding_without_id_does_not_crash(self):
        run_scan(self.root, "init")
        state = self.state()
        state["findings"].append({"severity": "low"})  # no 'id'
        (self.root / ".claude" / ".praxis" / "repo_scan.json").write_text(json.dumps(state))
        sid = state["shards"][0]["id"]
        out = run_scan(self.root, "finding", "add", "--shard", sid,
                       "--dimension", "edge-case", "--severity", "low",
                       "--file", "x.py", "--title", "t")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_corrupt_ledger_errors_instead_of_clobbering(self):
        run_scan(self.root, "init")
        ledger = self.root / ".claude" / ".praxis" / "repo_scan.json"
        ledger.write_text("{ not json")
        for args in (("status",), ("init",), ("mark", "S01", "adversarial")):
            out = run_scan(self.root, *args)
            self.assertEqual(out.returncode, 1)
            self.assertIn("cannot be parsed", out.stdout)
        self.assertEqual(run_scan(self.root, "clear").returncode, 1)  # corrupt → force
        self.assertEqual(run_scan(self.root, "clear", "--force").returncode, 0)
        self.assertEqual(run_scan(self.root, "init").returncode, 0)

    def test_clear_requires_force_on_recorded_work(self):
        run_scan(self.root, "init")
        out = run_scan(self.root, "clear")
        self.assertEqual(out.returncode, 1)
        self.assertTrue(self.state().get("shards"))  # untouched
        self.assertEqual(run_scan(self.root, "clear", "--force").returncode, 0)
        self.assertEqual(run_scan(self.root, "clear").returncode, 0)  # empty: no guard


class TestAuditTracking(RepoScanBase):
    def setUp(self):
        super().setUp()
        run_scan(self.root, "init")
        self.sid = self.state()["shards"][0]["id"]

    def test_mark_rejects_unknown_shard_and_dimension(self):
        self.assertEqual(run_scan(self.root, "mark", "S99", "adversarial").returncode, 1)
        self.assertEqual(run_scan(self.root, "mark", self.sid, "vibes").returncode, 1)

    def test_full_dimension_set_makes_shard_audited(self):
        for dim in repo_scan.DIMENSIONS:
            self.assertEqual(run_scan(self.root, "mark", self.sid, dim).returncode, 0)
        sh = next(s for s in self.state()["shards"] if s["id"] == self.sid)
        self.assertEqual(set(sh["done"]), set(repo_scan.DIMENSIONS))
        self.assertIn("fully audited", run_scan(self.root, "mark", self.sid, "edge-case").stdout)

    def test_mark_is_idempotent(self):
        run_scan(self.root, "mark", self.sid, "adversarial")
        run_scan(self.root, "mark", self.sid, "adversarial")
        sh = next(s for s in self.state()["shards"] if s["id"] == self.sid)
        self.assertEqual(sh["done"].count("adversarial"), 1)


class TestFindingLifecycle(RepoScanBase):
    def setUp(self):
        super().setUp()
        run_scan(self.root, "init")
        self.sid = self.state()["shards"][0]["id"]

    def add(self, sev="high"):
        out = run_scan(self.root, "finding", "add", "--shard", self.sid,
                       "--dimension", "adversarial", "--severity", sev,
                       "--file", "src/app.py", "--title", "unvalidated input")
        self.assertEqual(out.returncode, 0, out.stdout)
        return self.state()["findings"][-1]["id"]

    def test_add_validates_inputs(self):
        bad = run_scan(self.root, "finding", "add", "--shard", self.sid,
                       "--dimension", "adversarial", "--severity", "spicy",
                       "--file", "x", "--title", "t")
        self.assertEqual(bad.returncode, 1)
        missing = run_scan(self.root, "finding", "add", "--shard", self.sid)
        self.assertEqual(missing.returncode, 1)

    def test_verify_confirm_refute_downgrade(self):
        f1, f2, f3 = self.add(), self.add(), self.add()
        run_scan(self.root, "finding", "verify", f1, "--verdict", "confirmed")
        run_scan(self.root, "finding", "verify", f2, "--verdict", "refuted",
                 "--note", "guarded upstream")
        no_sev = run_scan(self.root, "finding", "verify", f3, "--verdict", "downgraded")
        self.assertEqual(no_sev.returncode, 1)  # downgrade requires a severity
        run_scan(self.root, "finding", "verify", f3, "--verdict", "downgraded",
                 "--severity", "low")
        by_id = {f["id"]: f for f in self.state()["findings"]}
        self.assertEqual(by_id[f1]["status"], "confirmed")
        self.assertEqual(by_id[f2]["status"], "refuted")
        self.assertEqual((by_id[f3]["status"], by_id[f3]["severity"]), ("confirmed", "low"))

    def test_fix_and_defer_require_confirmed(self):
        fid = self.add()
        self.assertEqual(run_scan(self.root, "finding", "fix", fid).returncode, 1)
        self.assertEqual(run_scan(self.root, "finding", "defer", fid,
                                  "--reason", "too big").returncode, 1)
        run_scan(self.root, "finding", "verify", fid, "--verdict", "confirmed")
        self.assertEqual(run_scan(self.root, "finding", "fix", fid,
                                  "--note", "sanitised in app.py").returncode, 0)
        self.assertEqual(self.state()["findings"][0]["status"], "fixed")

    def test_defer_requires_reason(self):
        fid = self.add()
        run_scan(self.root, "finding", "verify", fid, "--verdict", "confirmed")
        self.assertEqual(run_scan(self.root, "finding", "defer", fid).returncode, 1)
        self.assertEqual(run_scan(self.root, "finding", "defer", fid,
                                  "--reason", "needs schema migration").returncode, 0)

    def test_unknown_finding_id_fails(self):
        out = run_scan(self.root, "finding", "verify", "F999", "--verdict", "confirmed")
        self.assertEqual(out.returncode, 1)

    def test_ids_continue_from_max_recorded(self):
        self.add()
        self.add()
        self.assertEqual(self.state()["findings"][-1]["id"], "F002")
        self.assertEqual(repo_scan._next_finding_num(self.state()), 3)

    def test_secretlike_text_is_refused(self):
        fake_key = "sk_live_" + "a" * 24  # assembled so this file holds no signature
        out = run_scan(self.root, "finding", "add", "--shard", self.sid,
                       "--dimension", "adversarial", "--severity", "critical",
                       "--file", "config.py", "--title", f"hardcoded key {fake_key}")
        self.assertEqual(out.returncode, 1)
        self.assertIn("secret", out.stdout)
        self.assertEqual(self.state()["findings"], [])
        fid = self.add()
        out = run_scan(self.root, "finding", "verify", fid, "--verdict", "refuted",
                       "--note", f"value is {fake_key}")
        self.assertEqual(out.returncode, 1)
        self.assertEqual(self.state()["findings"][0]["status"], "open")

    def test_baseline_records_and_reports(self):
        bad = run_scan(self.root, "baseline", "--tests", "make test")
        self.assertEqual(bad.returncode, 1)
        ok = run_scan(self.root, "baseline", "--tests", "make test", "--exit", "1")
        self.assertEqual(ok.returncode, 0)
        self.assertIn("RED", ok.stdout)
        self.assertEqual(self.state()["baseline"]["exit"], 1)
        self.assertIn("make test", run_scan(self.root, "report").stdout)
        leaky = run_scan(self.root, "baseline", "--tests",
                         "TOKEN=" + "ghp_" + "a" * 36 + " pytest", "--exit", "0")
        self.assertEqual(leaky.returncode, 1)
        self.assertEqual(self.state()["baseline"]["command"], "make test")


class TestReport(RepoScanBase):
    def test_report_is_incomplete_until_every_shard_dimension_ran(self):
        run_scan(self.root, "init")
        self.assertIn("INCOMPLETE", run_scan(self.root, "report").stdout)
        for sh in self.state()["shards"]:
            for dim in repo_scan.DIMENSIONS:
                run_scan(self.root, "mark", sh["id"], dim)
        self.assertNotIn("INCOMPLETE", run_scan(self.root, "report").stdout)

    def test_commands_require_init(self):
        for args in (("status",), ("report",), ("shard", "S01"),
                     ("mark", "S01", "adversarial"), ("finding", "list")):
            self.assertEqual(run_scan(self.root, *args).returncode, 1)


class TestCommonWriteState(unittest.TestCase):
    def test_write_state_is_atomic_and_leaves_no_tmp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            common.write_state(root, "repo_scan.json", {"shards": [1, 2]})
            self.assertEqual(common.read_state(root, "repo_scan.json"), {"shards": [1, 2]})
            leftovers = list((root / ".claude" / ".praxis").glob("*.tmp"))
            self.assertEqual(leftovers, [])


class TestCommonListFiles(unittest.TestCase):
    def test_list_files_prunes_noise_and_ledger_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "node_modules" / "pkg" / "index.js").write_text("x")
            (root / ".claude" / ".praxis").mkdir(parents=True)
            (root / ".claude" / ".praxis" / "repo_scan.json").write_text("{}")
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("x")
            (root / "b.py").write_text("x")
            files = common.list_files(root)
            self.assertEqual(files, sorted(files))
            self.assertIn(str(Path("src") / "a.py"), files)
            self.assertFalse(any("node_modules" in f for f in files))
            self.assertFalse(any(".praxis" in f for f in files))
            self.assertEqual(common.list_files(root, limit=1), ["b.py"])

    def test_strict_state_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            common.write_state_strict(root, "x.json", {"a": 1})
            self.assertEqual(common.read_state_strict(root, "x.json"), {"a": 1})
            self.assertEqual(common.read_state_strict(root, "missing.json"), {})
            (root / ".claude" / ".praxis" / "x.json").write_text("{broken")
            with self.assertRaises(Exception):
                common.read_state_strict(root, "x.json")
            self.assertEqual(common.read_state(root, "x.json"), {})  # forgiving twin


if __name__ == "__main__":
    unittest.main()
