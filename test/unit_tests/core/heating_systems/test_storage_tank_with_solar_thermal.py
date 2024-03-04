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
from core.external_conditions import ExternalConditions
from core.material_properties import WATER, MaterialProperties
from core.heating_systems.storage_tank import StorageTank, ImmersionHeater, SolarThermalSystem
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.energy_supply.energy_supply import EnergySupply, EnergySupplyConnection
from core.controls.time_control import OnOffTimeControl

class Test_StorageTankWithSolarThermal(unittest.TestCase):
    """ Unit tests for StorageTank class """

    def setUp(self):
        """ Create StorageTank object to be tested """
        coldwatertemps = [17.0, 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.0, 17.1, 17.2, 17.3,
                             17.4, 17.5, 17.6, 17.7, 17.0, 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7]
        self.simtime     = SimulationTime(5088, 5112, 1)        
        coldfeed         = ColdWaterSource(coldwatertemps, self.simtime, 212, 1)
        control          = OnOffTimeControl(
                               [True, False, False, False, True, True, True, True],
                               self.simtime,
                               0,
                               1
                               )
        self.energysupply = EnergySupply("electricity", self.simtime)
        energysupplyconnst = self.energysupply.connection("solarthermal")

        #Adding solarthermal to the test
        proj_dict = {
            "ExternalConditions": {
                "air_temperatures": [19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 
                                        19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0],
                "wind_speeds": [3.9, 3.8, 3.9, 4.1, 3.8, 4.2, 4.3, 4.1, 3.9, 3.8, 3.9, 4.1, 
                                    3.8, 4.2, 4.3, 4.1, 3.9, 3.8, 3.9, 4.1, 3.8, 4.2, 4.3, 4.1],
                "diffuse_horizontal_radiation": [0, 0, 0, 0, 35, 73, 139, 244, 320, 361, 369, 348, 
                                                    318, 249, 225, 198, 121, 68, 19, 0, 0, 0, 0, 0],
                "direct_beam_radiation": [0, 0, 0, 0, 0, 0, 7, 53, 63, 164, 339, 242, 
                                            315, 577, 385, 285, 332, 126, 7, 0, 0, 0, 0, 0],
                "solar_reflectivity_of_ground": [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 
                                                    0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
                "latitude": 51.383,
                "longitude": -0.783,
                "timezone": 0,
                "start_day": 212,
                "end_day": 212,
                "time_series_step": 1,
                "january_first": 1,
                "daylight_savings": "not applicable",
                "leap_day_included": False,
                "direct_beam_conversion_needed": False,
                "shading_segments":[
            {"number": 1, "start": 180, "end": 135},
            {"number": 2, "start": 135, "end": 90},
            {"number": 3, "start": 90, "end": 45},
            {"number": 4, "start": 45, "end": 0, 
                "shading": [
                    {"type": "obstacle", "height": 10.5, "distance": 120}
                ]
            },
            {"number": 5, "start": 0, "end": -45},
            {"number": 6, "start": -45, "end": -90},
            {"number": 7, "start": -90, "end": -135},
            {"number": 8, "start": -135, "end": -180}
        ],
            }
        }
        self.__external_conditions = ExternalConditions(
            self.simtime,
            proj_dict['ExternalConditions']['air_temperatures'],
            proj_dict['ExternalConditions']['wind_speeds'],
            proj_dict['ExternalConditions']['diffuse_horizontal_radiation'],
            proj_dict['ExternalConditions']['direct_beam_radiation'],
            proj_dict['ExternalConditions']['solar_reflectivity_of_ground'],
            proj_dict['ExternalConditions']['latitude'],
            proj_dict['ExternalConditions']['longitude'],
            proj_dict['ExternalConditions']['timezone'],
            proj_dict['ExternalConditions']['start_day'],
            proj_dict['ExternalConditions']['end_day'],
            proj_dict['ExternalConditions']["time_series_step"],
            proj_dict['ExternalConditions']['january_first'],
            proj_dict['ExternalConditions']['daylight_savings'],
            proj_dict['ExternalConditions']['leap_day_included'],
            proj_dict['ExternalConditions']['direct_beam_conversion_needed'],
            proj_dict['ExternalConditions']['shading_segments']
            )
        self.solthermal  = SolarThermalSystem("OUT", 3, 1, 0.8, 0.9, 3.5, 0, 1, 100, 10, 
                                              energysupplyconnst, 30, 0, 0.5, 
                                              self.__external_conditions, self.simtime
                                              )
        heat_source_dict = {self.solthermal: (0.1, 0.33)}
        self.storagetank = StorageTank(150.0, 1.68, 52.0, 55.0, coldfeed, self.simtime, heat_source_dict)

    def test_demand_hot_water(self):
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.storagetank.demand_hot_water([100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                                   0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                                   0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                                                  [t_idx])
                               
                self.assertAlmostEqual(
                    self.storagetank.test_energy_demand(),
                    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                     0.3944013153635651, 0.7205382866008986, 
                     1.1792815529120688, 0.9563670953583516, 
                     1.066201484260018, 0.2842009512268733, 
                     0.07050814814814632, 0.07050814814814682,
                     0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0][t_idx],
                    msg="incorrect energy demand from tank",
                    )
                self.assertAlmostEqual(
                    self.solthermal.test_energy_potential(),
                    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                     0.3944013153635651, 0.7205382866008986, 
                     1.1792815529120688, 0.9563670953583516, 
                     1.066201484260018, 1.3754941274949404, 
                     0.788682346923819, 0.4490991945005249,
                     0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0][t_idx],
                    msg="incorrect energy potential by solar thermal returned",
                    )
                self.assertAlmostEqual(
                    self.solthermal.test_energy_supplied(),
                    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                     0.3944013153635651, 0.7205382866008986, 
                     1.1792815529120688, 0.9563670953583516, 
                     1.066201484260018, 0.2842009512268733, 
                     0.07050814814814632, 0.07050814814814682,
                     0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0][t_idx],
                    msg="incorrect energy supplied by solar thermal returned",
                    )
                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()["solarthermal"][t_idx],
                    [10, 10, 10, 10, 10, 10, 10, 10,
                     110, 110, 110, 110, 110, 110, 110, 110,
                     10, 10, 10, 10, 10, 10, 10, 10,][t_idx],
                    msg="incorrect electric energy consumed returned",
                    )
