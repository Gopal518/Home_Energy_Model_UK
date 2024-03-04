#!/usr/bin/env python3

"""
This module contains unit tests for the other water uses module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.water_heat_demand.other_hot_water_uses import OtherHotWater

class TestOtherHotWater(unittest.TestCase):
    """ Unit tests for OtherHotWater class """

    def setUp(self):
        """ Create OtherWaterUses object to be tested """
        self.simtime         = SimulationTime(0, 3, 1)
        coldwatertemps       = [2.0, 3.0, 4.0]
        self.coldwatersource = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        self.otherhotwater   = OtherHotWater(5.0, self.coldwatersource)

    def test_get_flowrate(self):
        """ Test that OtherWaterUses object returns correct flow rate """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.otherhotwater.get_flowrate(),
                    5.0,
                    "incorrect flow rate returned"
                    )

    def test_get_cold_water_source(self):
        """ Test the cold water source is created as expected """
        self.assertIs(
            self.coldwatersource,
            self.otherhotwater.get_cold_water_source(),
            "cold water source not returned"
            )

    def test_hot_water_demand(self):
        """ Test that OtherWaterUses object returns correct hot water demand """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.otherhotwater.hot_water_demand(40.0, 4.0),
                    [15.2, 15.102, 15.0][t_idx],
                    3,
                    "incorrect hot water demand returned"
                    )