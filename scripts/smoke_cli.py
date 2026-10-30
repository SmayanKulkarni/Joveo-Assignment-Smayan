"""Live smoke test, not run in CI. Drives `scout run` through the stub Pauses with the real check_balance."""
import tempfile
from pathlib import Path

from talent_scout.clients import cli
from talent_scout.kernel.settings import get_settings


def main():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        # A scratch Runs folder, so the smoke leaves nothing in .cache or runs/.
        settings = get_settings().model_copy(update={"runs_db": root / "runs.sqlite", "runs_dir": root / "runs"})
        cli.get_settings = lambda: settings
        # The real clarify loop asks a variable number of questions, so answer by prompt:
        # option 1 for a question, approve the plan, continue on low data.
        cli.input = lambda prompt="": "1" if prompt.startswith("Answer") else "a" if "[a]" in prompt else "c"
        code = cli.main(["run", "Engineer, Texas", "--focus", "skills"])
        print("exit code:", code)


if __name__ == "__main__":
    main()
