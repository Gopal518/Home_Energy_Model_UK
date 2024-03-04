#!/usr/bin/env python3

"""
This module contains unit tests for the Electric Storage Heater module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.energy_supply.energy_supply import EnergySupplyConnection, EnergySupply
from core.heating_systems.elec_storage_heater import ElecStorageHeater
from core.controls.time_control import ToUChargeControl, SetpointTimeControl

class TestElecStorageHeater(unittest.TestCase):
    """ Unit tests for ElecStorageHeater class """

    def setUp(self):
        """ Create ElecStorageHeater object to be tested """

        class Zone:
            def temp_internal_air(self):
                return 20.0

        zone = Zone()

        self.simtime     = SimulationTime(0, 24, 1)
        energysupply     = EnergySupply("electricity", self.simtime)
        energysupplyconn = energysupply.connection("main")
        control          = SetpointTimeControl([15.0, 15.0, 15.0, 15.0, 
                                                15.0, 15.0, 15.0, 21.0, 
                                                21.0, 21.0, 21.0, 21.0, 
                                                21.0, 21.0, 21.0, 21.0,
                                                21.0, 21.0, 21.0, 21.0, 
                                                15.0, 15.0, 15.0, 15.0], self.simtime, 0, 1)
        charge_control   = ToUChargeControl([True, True, True, True, 
                                             True, True, True, True, 
                                             False, False, False, False,
                                             False, False, False, False, 
                                             True, True, True, True, 
                                             False, False, False, False], self.simtime, 0, 1, [ 1.0, 0.8 ])

        data = {"rated_power": 4.0,
                "rated_power_instant": 0.75,
                "air_flow_type": "fan-assisted",
                "temp_dis_safe": 60.0,
                "thermal_mass": 0.01278,
                "frac_convective": 0.7,
                "U_ins": 0.3,
                "temp_charge_cut": 15.5,
                "mass_core": 130.0,
                "c_pcore": 920.0,
                "temp_core_target": 450.0,
                "A_core": 4.0,
                "c_wall": 8.0,
                "n_wall": 0.9,
                "thermal_mass_wall": 23.0,
                "fan_pwr": 11.0,
                "n_units": 2}

        self.elecstorageheater = ElecStorageHeater(data['rated_power'],
                                               data['rated_power_instant'],
                                               data['air_flow_type'],
                                               data['temp_dis_safe'],
                                               data['thermal_mass'],
                                               data['frac_convective'],
                                               data['U_ins'],
                                               data['temp_charge_cut'],
                                               data['mass_core'],
                                               data['c_pcore'],
                                               data['temp_core_target'],
                                               data['A_core'],
                                               data['c_wall'],
                                               data['n_wall'],
                                               data['thermal_mass_wall'],
                                               data['fan_pwr'],
                                               data['n_units'],
                                               zone,
                                               energysupplyconn,
                                               self.simtime,
                                               control,
                                               charge_control)

    def test_demand_energy(self):
        """ Test that ElecStorageHeater object returns correct energy supplied """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    round(self.elecstorageheater.demand_energy([4.69, 3.59, 4.26, 2.82, 
                                                                0.31, 3.72, 2.11, 6.55, 
                                                                7.59, 7.55, 4.52, 2.92, 
                                                                3.42, 5.83, 4.26, 3.63, 
                                                                4.38, 5.34, 4.65, 3.85, 
                                                                0, 1.86, 2.27, 2.62 ][t_idx]), 2),
                    [3.18, 2.93, 2.71, 2.49,
                     0.31, 2.26, 2.11, 2.03,
                     1.95, 1.9, 1.86, 1.81,
                     1.77, 1.73, 1.7, 1.67,
                     1.65, 1.63, 1.61, 1.6,
                     0.02, 1.58, 1.57, 1.56][t_idx],
                    "incorrect energy supplied returned",
                    )
