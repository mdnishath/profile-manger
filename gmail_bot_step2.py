"""
Gmail Bot - Step 2 (Full Account Operations)
Entry point — delegates all work to step2/ and shared/ modules.
"""

import sys
from step2.runner import GmailBotWorker
from shared.worker_runner import start_production_processing as _run


def start_production_processing(excel_file, num_workers=10, bot_step=2):
    """Start Step 2 multi-worker processing."""
    _run(
        excel_file=excel_file,
        num_workers=num_workers,
        worker_class=GmailBotWorker,
        step_banner='GMAIL BOT - STEP 2 (Full Operations)',
        step_name='step2',
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
