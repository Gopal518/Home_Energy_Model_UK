#!/usr/bin/env python3

"""
This module contains unit tests for the pipework module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.pipework import Pipework

class TestPipework(unittest.TestCase):
    """ Unit tests for Pipework class """

    def setUp(self):
        """ Create Pipework object to be tested """
        self.simtime = SimulationTime(0, 8, 1)
        self.pipework = Pipework(0.025, 0.027, 1.0, 0.035, 0.038, False, 'water')

    def test_interior_surface_resistance(self):
        """ Test that correct interior surface resistance is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__interior_surface_resistance, 0.00849, 5, msg="incorrect R1 returned")

    def test_insulation_resistance(self):
        """ Test that correct insulation resistance is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__insulation_resistance, 6.43829, 5, msg="incorrect R2 returned")

    def test_external_surface_resistance(self):
        """ Test that correct external surface resistance is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__external_surface_resistance, 0.30904, 5, msg="incorrect R3 returned")

    def test_heat_loss(self):
        """ Test that correct heat_loss is returned when queried """
        T_i = [50.0, 51.0, 52.0, 52.0, 51.0, 50.0, 51.0, 52.0]
        T_o = [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 21.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(self.pipework.heat_loss(T_i[t_idx], T_o[t_idx]),
                                 [5.18072, 5.18072, 5.18072, 5.03270, 4.73666, 4.44062, 4.44062, 4.58864][t_idx],
                                 5,
                                 msg="incorrect heat loss returned")

    def test_temp_drop(self):
        """ Test that correct temperature drop is returned when queried """
        T_i = [50.0, 51.0, 52.0, 52.0, 51.0, 50.0, 51.0, 52.0]
        T_o = [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 21.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(self.pipework.temperature_drop(T_i[t_idx], T_o[t_idx]),
                                 [35.0, 35.0, 35.0, 34.0, 32.0, 30.0, 30.0, 31.0][t_idx],
                                 5,
                                 msg="incorrect temperature drop returned")

    def test_cool_down_loss(self):
        """ Test that correct cool down loss is returned when queried """
        T_i = [50.0, 51.0, 52.0, 52.0, 51.0, 50.0, 51.0, 52.0]
        T_o = [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 21.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(self.pipework.cool_down_loss(T_i[t_idx], T_o[t_idx]),
                                 [0.01997, 0.01997, 0.01997, 0.01940, 0.01826, 0.01712, 0.01712, 0.01769][t_idx],
                                 5,
                                 msg="incorrect cool down loss returned")
