"""Console script entry point for ask-james."""
from .server import main as server_main


def main() -> None:  # pragma: no cover
    server_main()


if __name__ == "__main__":  # pragma: no cover
    main()
