"""
Gmail Bot - Linked Multi-Step Mode
Entry point — runs multiple steps in a single browser session per account.
"""

import json
import sys
from linked.runner import LinkedWorker
from shared.worker_runner import start_production_processing as _run


def start_production_processing(excel_file, num_workers=10, steps_config=None):
    """Start linked multi-step processing."""
    steps = steps_config.get('steps', [1, 2]) if steps_config else [1, 2]
    step_label = '+'.join(str(s) for s in steps)

    # Create a factory that passes steps_config to each LinkedWorker
    class _ConfiguredLinkedWorker(LinkedWorker):
        def __init__(self, worker_id, excel_processor):
            super().__init__(worker_id, excel_processor, steps_config=steps_config)

    _run(
        excel_file=excel_file,
        num_workers=num_workers,
        worker_class=_ConfiguredLinkedWorker,
        step_banner=f'GMAIL BOT - LINKED Steps {step_label}',
    )


if __name__ == "__main__":
    excel_file = "input/accounts.xlsx"
    num_workers = 10
    steps_config = {'steps': [1, 2], 'ops_per_step': {}}

    if len(sys.argv) > 1:
        excel_file = sys.argv[1]

    if len(sys.argv) > 2:
        try:
            num_workers = int(sys.argv[2])
        except ValueError:
            print(f"[ERROR] Invalid worker count: {sys.argv[2]}, using default: 10", flush=True)
            num_workers = 10

    if len(sys.argv) > 3:
        try:
            steps_config = json.loads(sys.argv[3])
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ERROR] Invalid steps JSON: {e}", flush=True)
            print(f"[ERROR] Using default: steps=[1,2]", flush=True)

    start_production_processing(excel_file, num_workers=num_workers, steps_config=steps_config)
