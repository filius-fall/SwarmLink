import argparse
import time

from main import SwarmLinkNode


def parse_args() -> argparse.Namespace:
    """Parse command-line options for launching one SwarmLink node.

    Why this helper exists:
    - Keeps argument parsing separated from launch logic.
    - Makes this file easier to extend for future dev/testing flags.
    """

    parser = argparse.ArgumentParser(
        description="Run one SwarmLink node with configurable name and TCP port."
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Display name for this node (defaults to hostname).",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=6001,
        help="TCP port this node listens on.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive CLI loop (useful outside containers).",
    )
    return parser.parse_args()


def run_non_interactive(node: SwarmLinkNode) -> None:
    """Keep the node alive without CLI input.

    Why this mode exists:
    - Containerized multi-node simulations are usually non-interactive.
    - We still want discovery, chat server, and file server threads active.
    """

    while not node.shutdown_event.is_set():
        time.sleep(1)


def main() -> None:
    args = parse_args()

    node = SwarmLinkNode(tcp_port=args.tcp_port, name=args.name)
    node.start()

    if args.interactive:
        node.run_cli()
        return

    try:
        run_non_interactive(node)
    except KeyboardInterrupt:
        node.shutdown_event.set()
        print("Shutting down...")


if __name__ == "__main__":
    main()
