"""CLI behavior: subcommands, flags, lazy/forced reconfigure, custom paths, compdb."""

import json
import time

from conftest import assert_output_contains_needles

DUMMY_BOBFILE_OUTPUT_CONTENTS = "hi"
DUMMY_BOBFILE_OUTPUT_FILE = "h.txt"
DUMMY_BOBFILE = f'rule("printf {DUMMY_BOBFILE_OUTPUT_CONTENTS} > $out").build("{DUMMY_BOBFILE_OUTPUT_FILE}")'


def test_build_creates_output(bob):
    bob.write(DUMMY_BOBFILE)
    bob.run("build")
    assert bob.output_text(DUMMY_BOBFILE_OUTPUT_FILE) == DUMMY_BOBFILE_OUTPUT_CONTENTS


def test_build_custom_builddir(bob):
    bob.write(DUMMY_BOBFILE)
    bob.run("build", "--builddir", "out")
    assert (bob.tmp_path / "out" / DUMMY_BOBFILE_OUTPUT_FILE).exists()
    assert not bob.build.exists()


def test_build_custom_bobfile_name(bob):
    bob.write(DUMMY_BOBFILE, name="Tomatofile.py")
    bob.run("build", "-f", "Tomatofile.py")
    assert bob.output_text(DUMMY_BOBFILE_OUTPUT_FILE) == DUMMY_BOBFILE_OUTPUT_CONTENTS


def test_build_doesnt_reconfigure(bob):
    bob.write(DUMMY_BOBFILE)
    bob.run("build")
    time.sleep(0.1)
    mtime = bob.ninja.stat().st_mtime
    bob.run("build")
    assert bob.ninja.stat().st_mtime == mtime


def test_build_force_reconfigure(bob):
    bob.write(DUMMY_BOBFILE)
    bob.run("build")
    time.sleep(0.1)
    mtime = bob.ninja.stat().st_mtime
    bob.run("build", "-F")
    assert bob.ninja.stat().st_mtime > mtime


def test_build_reconfigure_on_config_change(bob):
    bob.write(DUMMY_BOBFILE)
    bob.run("build")
    time.sleep(0.1)
    mtime = bob.ninja.stat().st_mtime
    bob.run("build", configs={"ANY": "1"})
    assert bob.ninja.stat().st_mtime > mtime


def test_build_missing_bobfile_fails(bob):
    bob.run("build", "-f", "DoesNotExist", assert_succesful=False)


def test_configure_creates_ninja(bob):
    bob.write(DUMMY_BOBFILE)
    bob.run("configure")
    assert bob.ninja.exists()


def test_configure_doesnt_build(bob):
    bob.write(DUMMY_BOBFILE)
    bob.run("configure")
    assert not bob.output_path(DUMMY_BOBFILE_OUTPUT_FILE).exists()


def test_clean_removes_builddir(bob):
    bob.write(DUMMY_BOBFILE)
    bob.run("build")
    assert bob.build.exists()
    bob.run("clean")
    assert not bob.build.exists()


def test_partial_ninja_file_removed_on_error(bob):
    bob.write("""
        rule("echo > $out").build("first.txt")
        raise RuntimeError("boom")
    """)
    bob.run("build", assert_succesful=False)
    assert not bob.ninja.exists()


def test_compdb_includes_rule_with_compile_command(bob):
    (bob.tmp_path / "main.c").write_text("int main(void){return 0;}\n", "utf-8")
    bob.write("""
        cc = rule(
            "true",
            compile_command="clang -c $in -o $out",
        )
        cc("main.o", inputs=["main.c"])
    """)
    bob.run("compdb")
    cdb = json.loads((bob.build / "compile_commands.json").read_text("utf-8"))
    assert any(entry["file"].endswith("main.c") for entry in cdb), cdb


def test_compdb_skips_rule_without_compile_command(bob):
    bob.write("""
        plain = rule("echo > $out")
        plain("x.txt")
    """)
    bob.run("compdb")
    cdb = json.loads((bob.build / "compile_commands.json").read_text("utf-8"))
    assert cdb == [], cdb


def test_build_specific_target(bob):
    """`bob build <target>` forwards the target to ninja; other rules in
    the same Bobfile must NOT run."""
    bob.write("""
        rule("echo first > $out").build("first.txt")
        rule("echo second > $out").build("second.txt")
    """)
    bob.run("build", "build/first.txt")
    assert bob.output_text("first.txt").strip() == "first"
    assert not bob.output_path("second.txt").exists()


def test_unknown_subcommand_fails(bob):
    r = bob.run("not-a-command", assert_succesful=False)
    assert_output_contains_needles(r, "no such command")


def test_configure_writes_both_build_and_compdb_ninja(bob):
    """Configure produces build.ninja AND compdb.ninja in a single pass."""
    bob.write(DUMMY_BOBFILE)
    bob.run("configure")
    assert bob.ninja.exists()
    assert (bob.ninja.parent / "compdb.ninja").exists()


def test_symlink_compdb_flag_links_compile_commands_at_root(bob):
    """`bob build --symlink-compdb` links compile_commands.json into root."""
    bob.write(DUMMY_BOBFILE)
    bob.run("build", "--symlink-compdb")
    assert (bob.tmp_path / "compile_commands.json").exists()


def test_default_build_does_not_symlink_compdb_at_root(bob):
    """Without `--symlink-compdb`, no symlink is placed at the project root."""
    bob.write(DUMMY_BOBFILE)
    bob.run("build")
    assert not (bob.tmp_path / "compile_commands.json").exists()


def test_use_current_configs_replays_saved_configs(bob):
    """`bob configure --use-current-configs` reads bob_configs.json and
    re-applies the prior `-c MODE=on` without the caller resupplying it."""
    bob.write("""
        m = config("MODE", default="off")
        rule(f"echo {m} > $out").build("mode.txt")
    """)
    bob.run("build", configs={"MODE": "on"})
    assert bob.output_text("mode.txt").strip() == "on"

    bob.run("configure", "--use-current-configs")
    bob.run("build", "--use-current-configs")
    assert bob.output_text("mode.txt").strip() == "on"


def test_build_outside_builddir_requires_flag(bob):
    """A rule output path that escapes the builddir is rejected unless
    `--allow-build-outside-builddir` is set."""
    bob.write("""
        from pathlib import Path
        rule("echo hi > $out").build(Path("..") / "stray.txt")
    """)
    bob.run("build", assert_succesful=False)


def test_build_outside_builddir_allowed_with_flag(bob):
    bob.write("""
        from pathlib import Path
        rule("echo hi > $out").build(Path("..") / "stray.txt")
    """)
    bob.run("build", "--allow-build-outside-builddir")
    # The file lands one level above the builddir (i.e. at tmp_path).
    assert (bob.tmp_path / "stray.txt").read_text("utf-8").strip() == "hi"
