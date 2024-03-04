#!/usr/bin/env python3

"""
This module contains unit tests for the shower module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.energy_supply.energy_supply import EnergySupplyConnection, EnergySupply
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.water_heat_demand.shower import MixerShower, InstantElecShower

class TestMixerShower(unittest.TestCase):
    """ Unit tests for MixerShower class """

    def setUp(self):
        """ Create MixerShower object to be tested """
        self.simtime         = SimulationTime(0, 3, 1)
        coldwatertemps       = [2.0, 3.0, 4.0]
        coldwatersource      = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        self.mixershower     = MixerShower(6.5, coldwatersource)

    def test_hot_water_demand(self):
        """ Test that MixerShower object returns correct volume of hot water """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.mixershower.hot_water_demand(40.0, 5.0),
                    [24.7, 24.54081632653061, 24.375][t_idx],
                    "incorrect volume of hot water returned"
                    )

class TestInstantElecShower(unittest.TestCase):
    """ Unit tests for InstantElecShower class """

    def setUp(self):
        """ Create InstantElecShower object to be tested """
        self.simtime           = SimulationTime(0, 3, 1)
        coldwatertemps         = [2.0, 3.0, 4.0]
        coldwatersource        = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        self.energysupply      = EnergySupply("electricity", self.simtime)
        energysupplyconn       = self.energysupply.connection("shower")
        self.instantelecshower = InstantElecShower(50, coldwatersource, energysupplyconn)

    def test_hot_water_demand(self):
        """Test that there is a demand on the energy supply connection but that
        that no demand on the water heating system is returned
        """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                demand = self.instantelecshower.hot_water_demand(40.0, ((t_idx+1)*6))
                self.assertEqual(
                    self.energysupply.results_by_end_user()["shower"][t_idx],
                    [5.0, 10.0, 15.0][t_idx],
                    "correct electricity demand not returned"
                    )
                self.assertEqual(
                    self.instantelecshower.hot_water_demand(40.0, ((t_idx+1)*6)),
                    [86.04206500956023, 175.59605103991885, 268.8814531548757][t_idx],
                    "correct hot water demand not returned"
                    )
