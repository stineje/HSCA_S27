#!/bin/bash

# Exit on error
set -e

echo "Recursively searching for all 'work' directories..."

# Find and delete ALL directories named 'work' anywhere below the current directory
find . -type d -name "work" -exec rm -rf {} +

echo "All 'work' directories removed."
