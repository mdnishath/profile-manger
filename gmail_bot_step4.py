"""
Gmail Bot - Step 4 (Google Account Appeal Management)
Entry point — delegates all work to step4/ and shared/ modules.
"""

import sys
from step4.runner import GmailBotWorker
from shared.worker_runner import start_production_processing as _run


def start_production_processing(excel_file, num_workers=5):
    """Start Step 4 multi-worker processing."""
    _run(
        excel_file=excel_file,
        num_workers=num_workers,
        worker_class=GmailBotWorker,
        step_banner='GMAIL BOT - STEP 4 (Google Account Appeal Management)',
        step_name='step4',
    )


if __name__ == "__main__":
    excel_file  = "input/accounts.xlsx"
    num_workers = 5

    if len(sys.argv) > 1:
        excel_file = sys.argv[1]

    if len(sys.argv) > 2:
        try:
            num_workers = int(sys.argv[2])
        except ValueError:
            print(f"[ERROR] Invalid worker count: {sys.argv[2]}, using default: 5", flush=True)
            num_workers = 5

    start_production_processing(excel_file, num_workers=num_workers)
