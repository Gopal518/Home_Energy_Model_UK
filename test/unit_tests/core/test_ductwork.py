#!/usr/bin/env python3

"""
This module contains unit tests for the Ductwork module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.ductwork import Ductwork

class TestDuctwork(unittest.TestCase):
    """ Unit tests for Ductwork class """

    def setUp(self):
        """ Create Ductwork objects to be tested """
        self.ductwork = Ductwork(0.025, 0.027, 0.4, 0.4, 0.02, 0.022, False, "inside")
        self.simtime = SimulationTime(0, 8, 1)

    def test_D_ins(self):
        """ Test that correct D_ins value is returned when queried """
        self.assertAlmostEqual(
            self.ductwork._Ductwork__D_ins,
            0.071,
            3,
            "incorrect D_ins returned"
            )

    def test_internal_surface_resistance(self):
        """ Test that correct internal surface resistance value is returned when queried """
        self.assertAlmostEqual(
            self.ductwork._Ductwork__internal_surface_resistance ,
            0.82144,
            5,
            "incorrect internal surface resistance returned"
            )

    def test_insulation_resistance(self):
        """ Test that correct insulation resistance value is returned when queried """
        self.assertAlmostEqual(
            self.ductwork._Ductwork__insulation_resistance,
            8.30633,
            5,
            "incorrect insulation resistance returned"
            )

    def test_external_surface_resistance(self):
        """ Test that correct external surface resistance value is returned when queried """
        self.assertAlmostEqual(
            self.ductwork._Ductwork__external_surface_resistance,
            0.44832,
            5,
            "incorrect external surface resistance returned"
            )

    def test_duct_heat_loss(self):
        """ Test that correct heat loss is returned when queried """
        outside_temp = [20.0, 19.5, 19.0, 18.5, 19.0, 19.5, 20.0, 20.5]
        inside_temp = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(
                    self.ductwork.duct_heat_loss(inside_temp[t_idx], outside_temp[t_idx], 0.4),
                    [-0.62656, -0.56390, -0.50125, -0.43859, -0.41771, -0.39682, -0.37594, -0.35505][t_idx],
                    5,
                    "incorrect heat loss returned",
                    )

    def test_total_duct_heat_loss(self):
        """ Test that correct total duct heat loss is returned when queried """
        outside_temp = [20.0, 19.5, 19.0, 18.5, 19.0, 19.5, 20.0, 20.5]
        intake_temp = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
        exhaust_temp = [20.0, 19.5, 19.0, 18.5, 19.0, 19.5, 20.0, 20.5]
        supply_temp = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
        extract_temp = [20.0, 19.5, 19.0, 18.5, 19.0, 19.5, 20.0, 20.5]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(
                    self.ductwork.total_duct_heat_loss(outside_temp[t_idx], supply_temp[t_idx], extract_temp[t_idx], intake_temp[t_idx], exhaust_temp[t_idx], 0.7) ,
                    [-0.43859, -0.39473, -0.35087, -0.30701, -0.29239, -0.27777, -0.26316, -0.24854][t_idx],
                    5,
                    "incorrect total heat loss returned",
                    )
