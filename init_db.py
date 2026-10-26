#!/usr/bin/env python
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from init_db import init_database

if __name__ == '__main__':
    init_database()
