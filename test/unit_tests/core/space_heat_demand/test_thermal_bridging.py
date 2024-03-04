#!/usr/bin/env python3

"""
This module contains unit tests for the thermal_bridge module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.space_heat_demand.thermal_bridge import ThermalBridgeLinear, ThermalBridgePoint

class TestThermalBridgeLinear(unittest.TestCase):
    """ Unit tests for ThermalBridgeLinear class """

    def setUp(self):
        """ Create ThermalBridgeLinear object to be tested """
        self.tb = ThermalBridgeLinear(0.28, 5.0)

    def test_heat_trans_coeff(self):
        self.assertAlmostEqual(
            self.tb.heat_trans_coeff(),
            1.4,
            msg = 'incorrect heat transfer coeff returned'
            )


class TestThermalBridgePoint(unittest.TestCase):
    """ Unit tests for ThermalBridgePoint class """

    def setUp(self):
        """ Create ThermalBridgePoint object to be tested """
        self.tb = ThermalBridgePoint(1.4)

    def test_heat_trans_coeff(self):
        self.assertEqual(self.tb.heat_trans_coeff(), 1.4, 'incorrect heat transfer coeff returned')
