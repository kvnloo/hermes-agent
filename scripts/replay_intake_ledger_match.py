#!/usr/bin/env python3
"""Replay frozen labels through the production transaction, using disposable ledgers."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins'))
from intake_ledger_match.matcher import update_ledger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('labels', type=Path)
    parser.add_argument('ledger', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sequential', action='store_true')
    args = parser.parse_args()
    labels = json.loads(args.labels.read_text())['messages']
    snapshot = args.ledger.read_bytes()
    results = []
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'ledger.json'
        path.write_bytes(snapshot)
        for record in labels:
            if not args.sequential:
                path.write_bytes(snapshot)
            result = update_ledger(path, str(record['source_message_id']), record['text'])
            predicted = 'NEW' if result['action'] == 'new' else result['row_id']
            actual = json.loads(path.read_text())
            touched = next(row for row in actual if row['id'] == result['row_id'])
            assert str(record['source_message_id']) in touched['mentions']
            results.append({'id': record['id'], 'corpus_line': record['corpus_line'],
                            'expected': record['expected'], 'predicted': predicted,
                            'correct': predicted == record['expected'], 'score': result.get('score'),
                            'reason': record['reason']})
    correct = sum(record['correct'] for record in results)
    report = {'sequential': args.sequential, 'total': len(results), 'correct': correct, 'accuracy': correct / len(results),
              'seconds': round(time.monotonic() - started, 3),
              'confusion': [record for record in results if not record['correct']], 'results': results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if correct >= 18 and len(results) == 20 else 1


if __name__ == '__main__':
    raise SystemExit(main())
