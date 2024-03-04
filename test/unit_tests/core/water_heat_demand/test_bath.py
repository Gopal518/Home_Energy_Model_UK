#!/usr/bin/env python3

"""
This module contains unit tests for the bath module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.water_heat_demand.bath import Bath

class TestBath(unittest.TestCase):
    """ Unit tests for Bath class """

    def setUp(self):
        """ Create Bath object to be tested """
        self.simtime         = SimulationTime(0, 3, 1)
        coldwatertemps       = [2.0, 3.0, 4.0]
        self.coldwatersource = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        self.bath            = Bath(100.0, self.coldwatersource, 4.5)

    def test_get_size(self):
        """ Test that Bath object returns correct size of bath """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.bath.get_size(),
                    100.0,
                    "incorrect size of bath returned"
                    )

    def test_get_cold_water_source(self):
        """ Test the cold water source is created as expected """
        self.assertIs(
            self.coldwatersource,
            self.bath.get_cold_water_source(),
            "cold water source not returned"
            )

    def test_get_flowrate(self):
        """ Test that Bath object returns correct flow rate """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.bath.get_flowrate(),
                    4.5,
                    "incorrect flow rate returned"
                    )

    def test_hot_water_demand(self):
        """ Test that Bath object returns correct hot water demand """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.bath.hot_water_demand(40.0),
                    [76.0, 75.510, 75.0][t_idx],
                    3,
                    "incorrect hot water demand returned"
                    )
