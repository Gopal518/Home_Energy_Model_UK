#!/usr/bin/env python3

"""
This module contains functionality that is shared between unit tests
"""

import sys
import os

def test_setup():
    """Set up test environment"""

    # Add src folder to path so that packages can be imported into tests
    this_dir = os.path.dirname(__file__)
    proj_path = os.path.dirname(os.path.dirname(this_dir))
    src_path = os.path.join(proj_path, 'src')
    sys.path.append(os.path.abspath(src_path))
