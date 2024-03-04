#!/usr/bin/env python3

"""
This module contains unit tests for units module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.units import Celcius2Kelvin, Kelvin2Celcius, average_monthly_to_annual, \
    convert_profile_to_daily

class TestUnits(unittest.TestCase):
    """ Unit tests for free functions in units module """

    def test_temp_conversions(self):
        """ Test temperature conversions between Celcius and Kelvin """
        self.assertEqual(Celcius2Kelvin(20.0), 293.15, 'incorrect conversion of C to K')
        self.assertEqual(Kelvin2Celcius(5.0), -268.15, 'incorrect conversion of K to C')

        # Test round-trip conversion for range of temperatures
        for i in range (-10, 80):
            with self.subTest(i=i):
                self.assertEqual(
                    Kelvin2Celcius(Celcius2Kelvin(i)),
                    i,
                    'round trip temperature conversion (C to K to C) failed to return orig value'
                    )

    def test_average_monthly_to_annual(self):
        """ Test conversion from monthly averages and annual average """
        list_monthly_averages = [4.3, 4.9, 6.5, 8.9, 11.7, 14.6, 16.6, 16.4, 14.1, 10.6, 7.1, 4.2]
        self.assertEqual(
            average_monthly_to_annual(list_monthly_averages),
            10.020547945205479,
            "incorrect conversion of monthly averages to annual average",
            )

    def test_convert_profile_to_daily(self):
        """ Test conversion from per-timestep profile to daily profile """
        list_timestep_totals = [1.0] * 48 + [x/2 for x in range(0, 48)]
        self.assertEqual(
            convert_profile_to_daily(list_timestep_totals, 0.5),
            [48.0, 564.0],
            "incorrect conversion of per-timestep profile to daily profile",
            )

if __name__ == '__main__':
    unittest.main()
