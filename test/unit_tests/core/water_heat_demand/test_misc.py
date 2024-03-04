#!/usr/bin/env python3

"""
This module contains unit tests for the misc module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.water_heat_demand.misc import frac_hot_water
from core.water_heat_demand.misc import water_demand_to_kWh
from core.simulation_time import SimulationTime

class TestMisc(unittest.TestCase):
    """ Unit tests for functions in the misc.py file """
    def test_frac_hot_water(self):
        self.assertEqual(
            frac_hot_water(40, 55, 5),
            0.7,
            "incorrect fraction of hot water returned",
            )

    def test_water_demand_to_kWh(self):
        """ Test that correct water demand to kWh is returned when queried """
        litres_demand = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0]
        demand_temp = [40.0, 35.0, 37.0, 39.0, 40.0, 38.0, 39.0, 40.0]
        cold_temp = [5.0, 4.0, 5.0, 6.0, 5.0, 4.0, 3.0, 4.0]
        for t_idx, _, _ in SimulationTime(0, 8, 1):
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(water_demand_to_kWh(litres_demand[t_idx], demand_temp[t_idx], cold_temp[t_idx]),
                               [0.20339, 0.36029, 0.55787, 0.76707, 1.01694, 1.18547, 1.46440, 1.67360][t_idx],
                               5,
                               msg="incorrect water demand to kWh returned")