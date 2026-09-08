"""Kaivor API command."""

import argparse
import sys

from core.api.openai_server import serve


def run():
    parser = argparse.ArgumentParser(description="Run the Kaivor OpenAI-compatible API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args(sys.argv[2:])
    serve(args.host, args.port)
