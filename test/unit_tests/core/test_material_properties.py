#!/usr/bin/env python3

"""
This module contains unit tests for the material_properties module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.material_properties import MaterialProperties

class TestMaterialProperties(unittest.TestCase):
    """ Unit tests for MaterialProperties class """

    def setUp(self):
        """ Create MaterialProperties object to be tested """
        self.matprop = MaterialProperties(density=1.5, specific_heat_capacity=4184)

    def test_density(self):
        """ Test that correct density is returned when queried """
        self.assertEqual(self.matprop.density(), 1.5, "incorrect density returned")

    def test_specific_heat_capacity(self):
        """ Test that correct specific heat capacity is returned when queried """
        self.assertEqual(
            self.matprop.specific_heat_capacity(),
            4184,
            "incorrect specific heat capacity returned"
            )

    def test_volumetric_heat_capacity(self):
        """ Test that correct volumetric heat capacity has been calculated """
        self.assertEqual(
            self.matprop.volumetric_heat_capacity(),
            6276.0,
            "incorrect volumetric heat capacity"
            )

    def test_volumetric_energy_content(self):
        """ Test that correct volumetric energy content has been calculated """
        temp_high = 30.0
        temp_low = 20.0
        self.assertEqual(
            self.matprop.volumetric_energy_content_J_per_litre(temp_high, temp_low),
            62760.0,
            "incorrect volumetric energy content (J per litre)"
            )
        self.assertAlmostEqual(
            self.matprop.volumetric_energy_content_kWh_per_litre(temp_high, temp_low),
            0.01743333333,
            10,
            "incorrect volumetric energy content (kWh per litre)"
            )

if __name__ == '__main__':
    unittest.main()
