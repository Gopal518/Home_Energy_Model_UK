#!/usr/bin/env python3

"""
This module contains unit tests for the Instant Electric Heater module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.energy_supply.energy_supply import EnergySupplyConnection, EnergySupply
from core.space_heat_demand.internal_gains import InternalGains, ApplianceGains

class TestInternalGains(unittest.TestCase):
    """ Unit tests for InternalGains class """

    def setUp(self):
        """ Create InternalGains object to be tested """
        self.simtime                = SimulationTime(0, 4, 1)
        self.total_internal_gains   = [3.2, 4.6, 7.3, 5.2]
        self.internalgains          = InternalGains(self.total_internal_gains, self.simtime, 0, 1)

    def test_total_internal_gain(self):
        """ Test that InternalGains object returns correct internal gains and electricity demand"""
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.internalgains.total_internal_gain(10.0),
                    [32, 46, 73, 52][t_idx],
                    "incorrect internal gains returned",
                    )


class TestApplianceGains(unittest.TestCase):
    """ Unit tests for ApplianceGains class """

    def setUp(self):
        """ Create ApplianceGains object to be tested """
        self.simtime                = SimulationTime(0, 4, 1)
        self.energysupply           = EnergySupply("electricity", self.simtime)
        energysupplyconn            = self.energysupply.connection("lighting")
        self.total_energy_supply    = [32.0, 46.0, 30.0, 20.0]
        self.appliancegains         = ApplianceGains(self.total_energy_supply, energysupplyconn, 0.5, self.simtime, 0, 1)

    def test_total_internal_gain(self):
        """ Test that ApplianceGains object returns correct internal gains and electricity demand"""
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.appliancegains.total_internal_gain(10.0),
                    [160.0, 230.0, 150.0, 100.0][t_idx],
                    "incorrect internal gains for appliances returned",
                    )
                self.assertEqual(
                    self.energysupply.results_by_end_user()["lighting"][t_idx],
                    [0.32, 0.46, 0.30, 0.20][t_idx],
                    "incorrect electricity demand  returned"
                    )
