#!/usr/bin/env python3

"""
This module contains unit tests for the external_conditions module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.external_conditions import ExternalConditions

class TestExternalConditions(unittest.TestCase):
    """ Unit tests for ExternalConditions class """

    def setUp(self):
        """ Create ExternalConditions object to be tested """
        self.simtime = SimulationTime(0, 8, 1)

        air_temp_day_Jan = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 7.5,
                            10.0, 12.5, 15.0, 19.5, 17.0, 15.0, 12.0, 10.0, 7.0, 5.0, 3.0, 1.0
                           ]
        air_temp_day_Feb = [x + 1.0 for x in air_temp_day_Jan]
        air_temp_day_Mar = [x + 2.0 for x in air_temp_day_Jan]
        air_temp_day_Apr = [x + 3.0 for x in air_temp_day_Jan]
        air_temp_day_May = [x + 4.0 for x in air_temp_day_Jan]
        air_temp_day_Jun = [x + 5.0 for x in air_temp_day_Jan]
        air_temp_day_Jul = [x + 6.0 for x in air_temp_day_Jan]
        air_temp_day_Aug = [x + 6.0 for x in air_temp_day_Jan]
        air_temp_day_Sep = [x + 5.0 for x in air_temp_day_Jan]
        air_temp_day_Oct = [x + 4.0 for x in air_temp_day_Jan]
        air_temp_day_Nov = [x + 3.0 for x in air_temp_day_Jan]
        air_temp_day_Dec = [x + 2.0 for x in air_temp_day_Jan]

        self.airtemp = []
        self.airtemp.extend(air_temp_day_Jan * 31)
        self.airtemp.extend(air_temp_day_Feb * 28)
        self.airtemp.extend(air_temp_day_Mar * 31)
        self.airtemp.extend(air_temp_day_Apr * 30)
        self.airtemp.extend(air_temp_day_May * 31)
        self.airtemp.extend(air_temp_day_Jun * 30)
        self.airtemp.extend(air_temp_day_Jul * 31)
        self.airtemp.extend(air_temp_day_Aug * 31)
        self.airtemp.extend(air_temp_day_Sep * 30)
        self.airtemp.extend(air_temp_day_Oct * 31)
        self.airtemp.extend(air_temp_day_Nov * 30)
        self.airtemp.extend(air_temp_day_Dec * 31)

        wind_speed_day_Jan = [4.7, 4.8, 4.9, 5.0, 5.1, 5.2, 5.3, 5.4, 5.7, 5.4, 5.6, 5.3,
                              5.1, 4.8, 4.7, 4.6, 4.5, 4.2, 4.9, 4.3, 4.4, 4.5, 4.3, 4.6
                           ]
        wind_speed_day_Feb = [x - 0.1 for x in wind_speed_day_Jan]
        wind_speed_day_Mar = [x - 0.2 for x in wind_speed_day_Jan]
        wind_speed_day_Apr = [x - 0.6 for x in wind_speed_day_Jan]
        wind_speed_day_May = [x - 0.8 for x in wind_speed_day_Jan]
        wind_speed_day_Jun = [x - 1.1 for x in wind_speed_day_Jan]
        wind_speed_day_Jul = [x - 1.2 for x in wind_speed_day_Jan]
        wind_speed_day_Aug = [x - 1.2 for x in wind_speed_day_Jan]
        wind_speed_day_Sep = [x - 1.1 for x in wind_speed_day_Jan]
        wind_speed_day_Oct = [x - 0.7 for x in wind_speed_day_Jan]
        wind_speed_day_Nov = [x - 0.5 for x in wind_speed_day_Jan]
        wind_speed_day_Dec = [x - 0.3 for x in wind_speed_day_Jan]

        self.windspeed = []
        self.windspeed.extend(wind_speed_day_Jan * 31)
        self.windspeed.extend(wind_speed_day_Feb * 28)
        self.windspeed.extend(wind_speed_day_Mar * 31)
        self.windspeed.extend(wind_speed_day_Apr * 30)
        self.windspeed.extend(wind_speed_day_May * 31)
        self.windspeed.extend(wind_speed_day_Jun * 30)
        self.windspeed.extend(wind_speed_day_Jul * 31)
        self.windspeed.extend(wind_speed_day_Aug * 31)
        self.windspeed.extend(wind_speed_day_Sep * 30)
        self.windspeed.extend(wind_speed_day_Oct * 31)
        self.windspeed.extend(wind_speed_day_Nov * 30)
        self.windspeed.extend(wind_speed_day_Dec * 31)

        self.diffuse_horizontal_radiation = [333, 610, 572, 420, 0, 10, 90, 275]
        self.direct_beam_radiation = [420, 750, 425, 500, 0, 40, 0, 388]

        self.solar_reflectivity_of_ground = [0.2] * 8760

        self.latitude = 51.42
        self.longitude = -0.75
        self.timezone = 0
        self.start_day = 0
        self.end_day = 0
        self.time_series_step = 1
        self.january_first = 1
        self.daylight_savings = "not applicable"
        self.leap_day_included = False
        self.direct_beam_conversion_needed = False
        self.shading_segments = [
            {"number": 1, "start": 180, "end": 135},
            {"number": 2, "start": 135, "end": 90},
            {"number": 3, "start": 90, "end": 45},
            {"number": 4, "start": 45, "end": 0},
            {"number": 5, "start": 0, "end": -45},
            {"number": 6, "start": -45, "end": -90},
            {"number": 7, "start": -90, "end": -135},
            {"number": 8, "start": -135, "end": -180}
        ]

        self.extcond = ExternalConditions(self.simtime,
                                          self.airtemp,
                                          self.windspeed,
                                          self.diffuse_horizontal_radiation,
                                          self.direct_beam_radiation,
                                          self.solar_reflectivity_of_ground,
                                          self.latitude,
                                          self.longitude,
                                          self.timezone,
                                          self.start_day,
                                          self.end_day,
                                          self.time_series_step,
                                          self.january_first,
                                          self.daylight_savings,
                                          self.leap_day_included,
                                          self.direct_beam_conversion_needed,
                                          self.shading_segments
                                        )

    def test_air_temp(self):
        """ Test that ExternalConditions object returns correct air temperatures """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.air_temp(),
                    self.airtemp[t_idx],
                    "incorrect air temp returned",
                    )

    def test_air_temp_annual(self):
        """ Test that ExternalConditions object returns correct annual air temperature """
        self.assertAlmostEqual(
            self.extcond.air_temp_annual(),
            10.1801369863014,
            msg="incorrect annual air temp returned"
            )

    def test_air_temp_monthly(self):
        """ Test that ExternalConditions object returns correct monthly air temperature """
        results = []
        for t_idx, _, _ in self.simtime:
            month_idx = self.simtime.current_month()
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.air_temp_monthly(),
                    [6.75, 7.75, 8.75, 9.75, 10.75, 11.75,
                     12.75, 12.75, 11.75, 10.75, 9.75, 8.75,
                    ][month_idx],
                    "incorrect monthly air temp returned",
                    )

    def test_wind_speed(self):
        """ Test that ExternalConditions object returns correct wind speeds"""
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.wind_speed(),
                    self.windspeed[t_idx],
                    "incorrect wind speed returned",
                    )

    def test_wind_speed_annual(self):
        """ Test that ExternalConditions object returns correct annual wind speed """
        self.assertAlmostEqual(
            self.extcond.wind_speed_annual(),
            4.23,
            2,
            msg="incorrect annual wind speed returned"
            )

    def test_diffuse_horizontal_radiation(self):
        """ Test that ExternalConditions object returns correct diffuse_horizontal_radiation """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.diffuse_horizontal_radiation(),
                    self.diffuse_horizontal_radiation[t_idx],
                    "incorrect diffuse_horizontal_radiation returned",
                    )
                
    def test_direct_beam_radiation(self):
        """ Test that ExternalConditions object returns correct direct_beam_radiation """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.direct_beam_radiation(),
                    self.direct_beam_radiation[t_idx],
                    "incorrect direct_beam_radiation returned",
                    )
                
    def test_solar_reflectivity_of_ground(self):
        """ Test that ExternalConditions object returns correct solar_reflectivity_of_ground """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.solar_reflectivity_of_ground(),
                    self.solar_reflectivity_of_ground[t_idx],
                    "incorrect solar_reflectivity_of_ground returned",
                    )
