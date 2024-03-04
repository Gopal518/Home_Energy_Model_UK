#!/usr/bin/env python3

"""
This module contains unit tests for the air conditioning module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.energy_supply.energy_supply import EnergySupplyConnection, EnergySupply
from core.cooling_systems.air_conditioning import AirConditioning
from core.controls.time_control import OnOffTimeControl

class TestAirConditioning(unittest.TestCase):
    """ Unit tests for AirConditioning class """

    def setUp(self):
        """ Create AirConditioning object to be tested """
        self.simtime            = SimulationTime(0, 4, 1)
        self.energysupply       = EnergySupply("electricity", self.simtime)
        energysupplyconn        = self.energysupply.connection("aircon")
        control                 = OnOffTimeControl([True, True, False, True], self.simtime, 0, 1)
        self.aircon = AirConditioning(50, 2.0, 0.4, energysupplyconn, self.simtime, control)

    def test_demand_energy(self):
        """ Test that AirConditioning object returns correct energy supplied """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                # Note: Cooling demands are negative by convention
                self.assertEqual(
                    self.aircon.demand_energy([-40.0, -100.0, -30.0, -20.0][t_idx]),
                    [-40.0, -50.0, 0.0, -20.0][t_idx],
                    "incorrect cooling energy supplied returned",
                    )
                self.assertEqual(
                    self.energysupply.results_by_end_user()['aircon'][t_idx],
                    [20.0, 25.0, 0.0, 10.0][t_idx],
                    "incorrect delivered energy demand returned",
                    )
