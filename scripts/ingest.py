import argparse

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.etl import ingest_file
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True)
    args = parser.parse_args()
    ingest_file(args.input)
