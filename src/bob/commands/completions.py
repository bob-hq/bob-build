import os
import shutil
import subprocess
import sys
from pathlib import Path

from bob.log import console


def completions(shell: str) -> None:
    bob = shutil.which("bob")
    assert bob is not None and Path(bob).resolve() == Path(sys.argv[0]).resolve(), (
        "You must be running a `bob` that is in the PATH to install shell completions!"
    )

    match shell:
        case "fish":
            completions_path = (
                Path.home() / ".config" / "fish" / "completions" / "bob.fish"
            )
            completions_path.parent.mkdir(parents=True, exist_ok=True)
            completion_script = subprocess.check_output(
                [bob], env={**os.environ, "_BOB_COMPLETE": f"{shell}_source"}
            )
            completions_path.write_bytes(completion_script)
            console.print(f"Completion script written to {completions_path}")
        case _:
            raise NotImplementedError(f'Completions are not supported for "{shell}"')
