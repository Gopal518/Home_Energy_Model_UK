#!/usr/bin/env python3

"""
This module contains unit tests for the simulation_time module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime

class TestSimulationTime(unittest.TestCase):
    """ Unit tests for SimulationTime class """

    def setUp(self):
        """ Create SimulationTime object to be tested """
        self.timestep = 0.5
        self.simtime = SimulationTime(742, 746, self.timestep)

    def test_timestep(self):
        """ Test that SimulationTime object returns correct timestep """
        self.assertEqual(self.simtime.timestep(), self.timestep, "incorrect timestep returned")

    def test_total_steps(self):
        """ Test that total steps has been calculated correctly """
        self.assertEqual(self.simtime.total_steps(), 8, "incorrect total steps")

    def test_iteration(self):
        """ Test that SimulationTime object works as an iterator """
        # Call to iter() should return reference to same object
        simtime_iter = iter(self.simtime)
        self.assertIs(simtime_iter, self.simtime)

        # Check figures returned in each iteration
        for i in range(0, 8):
            with self.subTest(i=i):
                # Check that call to next() returns correct index and current time
                self.assertEqual(
                    next(simtime_iter),
                    (i, i * self.timestep + 742, self.timestep),
                    "incorrect loop vars returned"
                    )

                # Check that individual functions also return correct index and current time
                self.assertEqual(
                    self.simtime.current(),
                    742 + i * self.simtime.timestep(),
                    "incorrect current time returned"
                    )
                self.assertEqual(self.simtime.index(), i, "incorrect ordinal index returned")
                self.assertEqual(
                    self.simtime.current_hour(),
                    [742, 742, 743, 743, 744, 744, 745, 745][i],
                    "incorrect current hour returned"
                    )
                self.assertEqual(
                    self.simtime.hour_of_day(),
                    [22, 22, 23, 23, 0, 0, 1, 1][i],
                    "incorrect hour of day returned"
                    )
                self.assertEqual(
                    self.simtime.current_day(),
                    [30, 30, 30, 30, 31, 31, 31, 31][i],
                    "incorrect current day returned"
                    )
                self.assertEqual(
                    self.simtime.time_series_idx(0, 1),
                    [742, 742, 743, 743, 744, 744, 745, 745][i],
                    "incorrect time series index returned"
                    )
                self.assertEqual(
                    self.simtime.current_month(),
                    [0, 0, 0, 0, 1, 1, 1, 1][i],
                    "incorrect current month returned"
                    )
                self.assertEqual(
                    self.simtime.current_month_start_end_hour(),
                    [(0, 744), (0, 744), (0, 744), (0, 744),
                     (744, 1416), (744, 1416), (744, 1416), (744, 1416)
                    ][i],
                    "incorrect start and end hours for current month returned"
                    )

        # Once all timesteps have been iterated over, next increment should raise exception
        with self.assertRaises(StopIteration):
            next(simtime_iter)
