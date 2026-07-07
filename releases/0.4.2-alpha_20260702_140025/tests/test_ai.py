"""
Kaivor AI Test
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.brain import Brain


def main():

    brain = Brain()

    print("✓ Brain initialised")

    print("✓ Provider:", brain.provider.__class__.__name__)


if __name__ == "__main__":
    main()