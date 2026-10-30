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
        replies = iter(["1", "a", "c"])  # clarify option 1, approve the plan, continue on low data
        cli.input = lambda _="": next(replies)
        code = cli.main(["run", "Engineer, Texas", "--focus", "skills"])
        print("exit code:", code)


if __name__ == "__main__":
    main()
