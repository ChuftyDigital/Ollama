"""Allow running with: python -m motorcycle-comparison-agent"""
import sys
import os

# Ensure the parent directory is on the path so `src` resolves
sys.path.insert(0, os.path.dirname(__file__))

from src.agent import main

main()
