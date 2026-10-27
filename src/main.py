"""Application entry point."""

import sys
import traceback

from src.ui.app import run


def main() -> int:
    """Run the TUI and report unexpected failures without a raw traceback."""
    try:
        run()
    except KeyboardInterrupt:
        print("\nAfgebroken door gebruiker.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"\nOnverwachte fout: {error}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print(
            "De provisioning is gestopt. Controleer de laatste status en logs.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
