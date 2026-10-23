"""Deterministic checks, optional real-model checks, nonzero status on failure."""
import argparse
import sys
import unittest
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',action='store_true',help='Also call the downloaded local model')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_*.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():return 1
    if args.model:
        sys.path.insert(0,str(root/'tests'))
        from live_model_check import run
        report=run()
        print(f"Real model checks: {report['passed']}/{report['total']}")
        return 0 if report['passed']==report['total']==8 else 1
    print('Model inference was NOT tested. Run with --model to validate real AI.')
    return 0


if __name__=='__main__':sys.exit(main())
