"""
Gmail Bot - Step 1 (Language Change + Sign Out)
Entry point — delegates all work to step1/ and shared/ modules.
"""

import sys
from step1.runner import GmailBotWorker
from shared.worker_runner import start_production_processing as _run


def start_production_processing(excel_file, num_workers=10):
    """Start Step 1 multi-worker processing."""
    _run(
        excel_file=excel_file,
        num_workers=num_workers,
        worker_class=GmailBotWorker,
        step_banner='GMAIL BOT - STEP 1 (Language Change + Sign Out)',
        step_name='step1',
    )


if __name__ == "__main__":
    excel_file  = "input/accounts.xlsx"
    num_workers = 10

    if len(sys.argv) > 1:
        excel_file = sys.argv[1]

    if len(sys.argv) > 2:
        try:
            num_workers = int(sys.argv[2])
        except ValueError:
            print(f"[ERROR] Invalid worker count: {sys.argv[2]}, using default: 10", flush=True)
            num_workers = 10

    start_production_processing(excel_file, num_workers=num_workers)
