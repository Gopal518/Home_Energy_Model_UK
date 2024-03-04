#!/usr/bin/env python3

"""
This module contains unit tests for the Storage Tank module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.material_properties import WATER, MaterialProperties
from core.heating_systems.storage_tank import StorageTank, ImmersionHeater
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.energy_supply.energy_supply import EnergySupply, EnergySupplyConnection
from core.controls.time_control import OnOffTimeControl

class Test_StorageTank(unittest.TestCase):
    """ Unit tests for StorageTank class """

    def setUp(self):
        """ Create StorageTank object to be tested """
        coldwatertemps = [10.0, 10.1, 10.2, 10.5, 10.6, 11.0, 11.5, 12.1]
        self.simtime     = SimulationTime(0, 8, 1)
        coldfeed         = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        control          = OnOffTimeControl(
                               [True, False, False, False, True, True, True, True],
                               self.simtime,
                               0,
                               1
                               )
        self.energysupply = EnergySupply("electricity", self.simtime)
        energysupplyconn = self.energysupply.connection("immersion")
        imheater         = ImmersionHeater(50.0, energysupplyconn, self.simtime, control)
        heat_source_dict = {imheater: (0.1, 0.33)}
        self.storagetank = StorageTank(150.0, 1.68, 52.0, 55.0, coldfeed, self.simtime, heat_source_dict)

        # Also test case where heater does not heat all layers, to ensure this is handled correctly
        energysupplyconn2 = self.energysupply.connection("immersion2")
        imheater2         = ImmersionHeater(5.0, energysupplyconn2, self.simtime, control)
        heat_source_dict2 = {imheater2: (0.6, 0.6)}
        self.storagetank2 = StorageTank(210.0, 1.61, 52.0, 60.0, coldfeed, self.simtime, heat_source_dict2)

    def test_demand_hot_water(self):
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.storagetank.demand_hot_water([10.0, 10.0, 15.0, 20.0, 20.0, 20.0, 20.0, 20.0]
                                                  [t_idx])
                #print(self.storagetank._StorageTank__temp_n)
                self.assertListEqual(
                    self.storagetank._StorageTank__temp_n,
                    [[43.5117037037037, 54.595555555555556, 54.595555555555556, 54.595555555555556],
                     [34.923351362284535, 51.44088940589104, 54.19530534979424, 54.19530534979424],
                     [25.428671888696492, 44.86111831060492, 52.763271736704276, 53.79920588690749],
                     [17.778914378539547, 34.731511258769736, 48.38455458241966, 52.883165319588585],
                     [55, 55, 55, 55],
                     [32.955654320987655, 54.595555555555556, 54.595555555555556, 54.595555555555556],
                     [55, 55, 55, 55],
                     [33.53623703703703, 54.595555555555556, 54.595555555555556, 54.595555555555556]][t_idx],
                    "incorrect temperatures returned"
                    )
                #print(self.energysupply.results_by_end_user()["immersion"][t_idx])
                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()["immersion"][t_idx],
                    [0.0,
                     0.0,
                     0.0,
                     0.0,
                     3.9189973050595626,
                     0.0,
                     2.0255553251028573,
                     0.0][t_idx],
                    msg="incorrect energy supplied returned",
                    )

                self.storagetank2.demand_hot_water([10.0, 10.0, 15.0, 20.0, 20.0, 20.0, 20.0, 20.0]
                                                  [t_idx])
                self.assertListEqual(
                    self.storagetank2._StorageTank__temp_n,
                    [[51.74444444444445, 59.687654320987654, 59.687654320987654, 59.687654320987654],
                     [44.83576096913369, 58.10817048730805, 59.37752591068435, 59.37752591068435],
                     [36.279411505184825, 54.60890513377094, 58.76352191705448, 59.06959902921961],
                     [27.803758539213316, 48.41088769491589, 57.11721566595131, 58.66493643832885],
                     [22.115012458237494, 41.46704433740872, 53.98882801141131, 57.857823384416925],
                     [18.392953648519935, 34.88146733500239, 60.0, 60.0],
                     [16.198781370486113, 29.539425498912564, 51.75379869179794, 59.687654320987654],
                     [14.889587258686573, 25.21241834280409, 60.0, 60.0],
                    ][t_idx],
                    "incorrect temperatures returned in case where heater does not heat all layers"
                    )
                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()["immersion2"][t_idx],
                    [0.0,
                     0.0,
                     0.0,
                     0.0,
                     0.0,
                     0.8689721305845337,
                     0.0,
                     1.1479005355748102,
                    ][t_idx],
                    msg="incorrect energy supplied returned in case where heater does not heat all layers",
                    )

class Test_ImmersionHeater(unittest.TestCase):
    """ Unit tests for ImmersionHeater class """

    def setUp(self):
        """ Create ImmersionHeater object to be tested """
        self.simtime          = SimulationTime(0, 4, 1)
        energysupply          = EnergySupply("mains_gas", self.simtime)
        energysupplyconn      = energysupply.connection("shower")
        control               = OnOffTimeControl([True, True, False, True], self.simtime, 0, 1)
        self.immersionheater  = ImmersionHeater(50, energysupplyconn, self.simtime, control)

    def test_demand_energy(self):
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.immersionheater.demand_energy([40.0, 100.0, 30.0, 20.0][t_idx]),
                    [40.0, 50.0, 0.0, 20.0][t_idx],
                    "incorrect energy supplied returned",
                    )
