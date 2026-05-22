"""C plugin: compile real binaries with clang and run them.

Assumes `clang` and `llvm-ar` are on $PATH.
"""

import subprocess


def _run_binary(path) -> str:
    p = subprocess.run([str(path)], capture_output=True, text=True, timeout=10)
    assert p.returncode == 0, f"{path} exited {p.returncode}: stderr={p.stderr!r}"
    return p.stdout.strip()


_TOOLCHAIN = 'import bob.plugins.c as c\nc.toolchain(ccbin="clang", arbin="llvm-ar")\n'


def test_binary_compiles_and_runs(bob):
    (bob.tmp_path / "main.c").write_text(
        '#include <stdio.h>\nint main(void){puts("ok"); return 0;}\n', "utf-8"
    )
    bob.write(_TOOLCHAIN + 'c.binary("hello", sources=["main.c"])')
    bob.run("build")
    assert _run_binary(bob.build / "hello") == "ok"


def test_cflags_extend_drives_compile_define(bob):
    (bob.tmp_path / "main.c").write_text(
        "#include <stdio.h>\n"
        "int main(void){\n"
        '#ifdef LOUD\n    puts("LOUD");\n'
        '#else\n    puts("quiet");\n'
        "#endif\n    return 0;}\n",
        "utf-8",
    )
    bob.write(
        _TOOLCHAIN
        + 'if config("LOUD") == "y":\n'
        + '    c.cflags.extend(["-DLOUD"])\n'
        + 'c.binary("app", sources=["main.c"])\n',
    )
    bob.run("build")
    assert _run_binary(bob.build / "app") == "quiet"
    bob.run("build", "-F", configs={"LOUD": "y"})
    assert _run_binary(bob.build / "app") == "LOUD"


def test_bundle_threads_public_cflags_into_consumer(bob):
    (bob.tmp_path / "include").mkdir()
    (bob.tmp_path / "include" / "lib.h").write_text("void greet(void);\n", "utf-8")
    (bob.tmp_path / "lib.c").write_text(
        '#include "lib.h"\n#include <stdio.h>\nvoid greet(void){puts("from lib");}\n',
        "utf-8",
    )
    (bob.tmp_path / "main.c").write_text(
        '#include "lib.h"\nint main(void){greet(); return 0;}\n', "utf-8"
    )
    bob.write(
        _TOOLCHAIN
        + 'bundle = c.static_library_bundle("greet", sources=["lib.c"], public_cflags=["-Iinclude"])\n'
        + 'c.binary("app", sources=["main.c"], bundles=[bundle])\n'
    )
    bob.run("build")
    assert _run_binary(bob.build / "app") == "from lib"
