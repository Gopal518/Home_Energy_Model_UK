#!/usr/bin/env python3

"""
This module contains unit tests for the cold_water_source module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.water_heat_demand.cold_water_source import ColdWaterSource

class TestColdWaterSource(unittest.TestCase):
    """ Unit tests for ColdWaterSource class """

    def setUp(self):
        """ Create ColdWaterSource object to be tested """
        self.simtime   = SimulationTime(0, 8, 1)
        self.watertemp = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        self.coldwater = ColdWaterSource(self.watertemp, self.simtime, 0, 1)

    def test_temperature(self):
        """ Test that ColdWaterSource object returns correct water temperatures """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.coldwater.temperature(),
                    self.watertemp[t_idx],
                    "incorrect water temp returned",
                    )
