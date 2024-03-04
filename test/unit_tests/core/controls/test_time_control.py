#!/usr/bin/env python3

"""
This module contains unit tests for the Time Control module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.controls.time_control import \
    OnOffTimeControl, SetpointTimeControl, OnOffCostMinimisingTimeControl

class Test_OnOffTimeControl(unittest.TestCase):
    """ Unit tests for OnOffTimeControl class """

    def setUp(self):
        """ Create TimeControl object to be tested """
        self.simtime     = SimulationTime(0, 8, 1)
        self.schedule    = [True, False, True, True, False, True, False, False]
        self.timecontrol = OnOffTimeControl(self.schedule, self.simtime, 0, 1)

    def test_is_on(self):
        """ Test that OnOffTimeControl object returns correct schedule"""
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.timecontrol.is_on(),
                    self.schedule[t_idx],
                    "incorrect schedule returned",
                    )


class Test_OnOffCostMinimisingTimeControl(unittest.TestCase):

    def setUp(self):
        self.simtime = SimulationTime(0, 48, 1)
        cost_schedule = 2 * ([5.0] * 7 + [10.0] * 2 + [7.5] * 8 + [15.0] * 6 + [5.0])
        self.cost_minimising_ctrl = OnOffCostMinimisingTimeControl(
            cost_schedule,
            self.simtime,
            0.0, # Start day
            1.0, # Schedule data is hourly
            12.0, # Need 12 "on" hours
            )

    def test_is_on(self):
        resulting_schedule \
            = 2 * ([True] * 7 + [False] * 2 + [True] * 4 + [False] * 4 + [False] * 6 + [True])
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.cost_minimising_ctrl.is_on(),
                    resulting_schedule[t_idx],
                    "incorrect schedule returned",
                    )


class Test_SetpointTimeControl(unittest.TestCase):
    """ Unit tests for SetpointTimeControl class """

    def setUp(self):
        """ Create TimeControl object to be tested """
        self.simtime     = SimulationTime(0, 8, 1)
        self.schedule    = [21.0, None, None, 21.0, None, 21.0, 25.0, 15.0]
        self.timecontrol = SetpointTimeControl(self.schedule, self.simtime, 0, 1)
        self.timecontrol_min \
            = SetpointTimeControl(self.schedule, self.simtime, 0, 1, 16.0, None)
        self.timecontrol_max \
            = SetpointTimeControl(self.schedule, self.simtime, 0, 1, None, 24.0)
        self.timecontrol_minmax \
            = SetpointTimeControl(self.schedule, self.simtime, 0, 1, 16.0, 24.0, False)
        self.timecontrol_advstart \
            = SetpointTimeControl(self.schedule, self.simtime, 0, 1, None, None, False, 1.0)
        self.timecontrol_advstart_minmax \
            = SetpointTimeControl(self.schedule, self.simtime, 0, 1, 16.0, 24.0, False, 1.0)

    def test_in_required_period(self):
        """ Test that SetpointTimeControl objects return correct status for required period """
        results = [True, False, False, True, False, True, True, True]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.timecontrol.in_required_period(),
                    results[t_idx],
                    "incorrect in_required_period value returned for control with no min or max set",
                    )
                self.assertEqual(
                    self.timecontrol_min.in_required_period(),
                    results[t_idx],
                    "incorrect in_required_period value returned for control with min set",
                    )
                self.assertEqual(
                    self.timecontrol_max.in_required_period(),
                    results[t_idx],
                    "incorrect in_required_period value returned for control with max set",
                    )
                self.assertEqual(
                    self.timecontrol_minmax.in_required_period(),
                    results[t_idx],
                    "incorrect in_required_period value returned for control with min and max set",
                    )
                self.assertEqual(
                    self.timecontrol_advstart.in_required_period(),
                    results[t_idx],
                    "incorrect in_required_period value returned for control with advanced start"
                    )
                self.assertEqual(
                    self.timecontrol_advstart_minmax.in_required_period(),
                    results[t_idx],
                    "incorrect in_required_period value returned for control with advanced start"
                    )

    def test_is_on(self):
        """ Test that SetpointTimeControl object is always on """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.timecontrol.is_on(),
                    [True, False, False, True, False, True, True, True][t_idx],
                    "incorrect is_on value returned for control with no min or max set",
                    )
                self.assertEqual(
                    self.timecontrol_min.is_on(),
                    True, # Should always be True for this type of control
                    "incorrect is_on value returned for control with min set",
                    )
                self.assertEqual(
                    self.timecontrol_max.is_on(),
                    True, # Should always be True for this type of control
                    "incorrect is_on value returned for control with max set",
                    )
                self.assertEqual(
                    self.timecontrol_minmax.is_on(),
                    True, # Should always be True for this type of control
                    "incorrect is_on value returned for control with min and max set",
                    )
                self.assertEqual(
                    self.timecontrol_advstart.is_on(),
                    [True, False, True, True, True, True, True, True][t_idx],
                    "incorrect is_on value returned for control with advanced start"
                    )
                self.assertEqual(
                    self.timecontrol_advstart_minmax.is_on(),
                    True,
                    "incorrect is_on value returned for control with advanced start"
                    )

    def test_setpnt(self):
        """ Test that SetpointTimeControl object returns correct schedule"""
        results_min             = [21.0, 16.0, 16.0, 21.0, 16.0, 21.0, 25.0, 16.0]
        results_max             = [21.0, 24.0, 24.0, 21.0, 24.0, 21.0, 24.0, 15.0]
        results_minmax          = [21.0, 16.0, 16.0, 21.0, 16.0, 21.0, 24.0, 16.0]
        results_advstart        = [21.0, None, 21.0, 21.0, 21.0, 21.0, 25.0, 15.0]
        results_advstart_minmax = [21.0, 16.0, 21.0, 21.0, 21.0, 21.0, 24.0, 16.0]

        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.timecontrol.setpnt(),
                    self.schedule[t_idx],
                    "incorrect schedule returned for control with no min or max set",
                    )
                self.assertEqual(
                    self.timecontrol_min.setpnt(),
                    results_min[t_idx],
                    "incorrect schedule returned for control with min set",
                    )
                self.assertEqual(
                    self.timecontrol_max.setpnt(),
                    results_max[t_idx],
                    "incorrect schedule returned for control with max set",
                    )
                self.assertEqual(
                    self.timecontrol_minmax.setpnt(),
                    results_minmax[t_idx],
                    "incorrect schedule returned for control with min and max set",
                    )
                self.assertEqual(
                    self.timecontrol_advstart.setpnt(),
                    results_advstart[t_idx],
                    "incorrect schedule returned for control with advanced start",
                    )
                self.assertEqual(
                    self.timecontrol_advstart_minmax.setpnt(),
                    results_advstart_minmax[t_idx],
                    "incorrect schedule returned for control with advanced start and min and max set",
                    )
