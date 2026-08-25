"""Compatibility entry point for the GitHub Actions workflow.

The workflow historically called alert_runner.py. The real scanner now lives in
otc_scanner.py, so this file deliberately delegates to it instead of maintaining
a second, outdated news-scoring implementation.
"""

from otc_scanner import run_scanner


if __name__ == "__main__":
    run_scanner()
