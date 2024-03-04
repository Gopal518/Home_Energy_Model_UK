#!/usr/bin/env python3

"""
This module contains unit tests for the Photovoltaic System module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.external_conditions import ExternalConditions
from core.energy_supply.energy_supply import EnergySupply, EnergySupplyConnection
from core.energy_supply.pv import PhotovoltaicSystem

class TestPhotovoltaicSystem(unittest.TestCase):
    """ Unit tests for PhotovoltaicSystem class """

    def setUp(self):
        """ Create PhotovoltaicSystem object to be tested """
        #simulation time: start, end, step
        self.simtime = SimulationTime(0, 8, 1)
        proj_dict = {
            "ExternalConditions": {
                "air_temperatures": [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0],
                "wind_speeds": [3.9, 3.8, 3.9, 4.1, 3.8, 4.2, 4.3, 4.1],
                "diffuse_horizontal_radiation": [11, 25, 42, 52, 60, 44, 28, 15],
                "direct_beam_radiation": [11, 25, 42, 52, 60, 44, 28, 15],
                "solar_reflectivity_of_ground": [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
                "latitude": 51.42,
                "longitude": -0.75,
                "timezone": 0,
                "start_day": 0,
                "end_day": 0,
                "time_series_step": 1,
                "january_first": 1,
                "daylight_savings": "not applicable",
                "leap_day_included": False,
                "direct_beam_conversion_needed": False,
                "shading_segments":[{"number": 1, "start": 180, "end": 135},
                                    {"number": 2, "start": 135, "end": 90,
                                     "shading": [
                                         {"type": "overhang", "height": 2.2, "distance": 6}
                                         ]
                                     },
                                    {"number": 3, "start": 90, "end": 45},
                                    {"number": 4, "start": 45, "end": 0, 
                                     "shading": [
                                         {"type": "obstacle", "height": 40, "distance": 4},
                                         {"type": "overhang", "height": 3, "distance": 7}
                                         ]
                                     },
                                    {"number": 5, "start": 0, "end": -45,
                                     "shading": [
                                         {"type": "obstacle", "height": 3, "distance": 8},
                                         ]
                                     },
                                    {"number": 6, "start": -45, "end": -90},
                                    {"number": 7, "start": -90, "end": -135},
                                    {"number": 8, "start": -135, "end": -180}],
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
        self.energysupply = EnergySupply("electricity", self.simtime)
        energysupplyconn = self.energysupply.connection("pv generation")
        self.pv_system = PhotovoltaicSystem(
                2.5,
                "moderately_ventilated",
                30,
                0,
                10,
                2,
                3,
                self.__external_conditions,
                energysupplyconn,
                self.simtime,
                )

    def test_produce_energy(self):
        """ Test that PhotovoltaicSystem object returns correct electricty generated kWh
            Note: produced energy stored as a negative demand"""
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.pv_system.produce_energy()
                decimal_places = 6
                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()["pv generation"][t_idx],
                    [-0.019039734375, -0.04586317375, -0.072234285625, -0.08283324375,
                     -0.089484801875, -0.074557144375, -0.05198861375, -0.040747119375][t_idx],
                    decimal_places,
                    "incorrect electricity produced from pv returned"
                    )
