#!/usr/bin/env python3

"""
This module contains unit tests for the building_element module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.external_conditions import ExternalConditions
from core.simulation_time import SimulationTime
from core.space_heat_demand.building_element import \
    BuildingElementOpaque, BuildingElementGround, BuildingElementTransparent, \
    BuildingElementAdjacentZTC, HeatFlowDirection

class TestBuildingElementOpaque(unittest.TestCase):
    """ Unit tests for BuildingElementOpaque class """

    def setUp(self):
        """ Create BuildingElementOpaque objects to be tested """
        self.simtime = SimulationTime(0, 4, 1)
        ec = ExternalConditions(self.simtime,
                                [0.0, 5.0, 10.0, 15.0],
                                None,
                                [0.0] * 4, # Diffuse horizontal radiation
                                [0.0] * 4, # Direct beam radiation
                                None,
                                55.0, # Latitude
                                0.0, # Longitude
                                0.0, # Timezone
                                0, # Start day
                                None,
                                1, # Time-series step,
                                None,
                                None,
                                None,
                                None,
                                None
                                )
        #TODO implement rest of external conditions in unit tests

        # Create an object for each mass distribution class
        be_I = BuildingElementOpaque(20, 180, 0.60, 0.25, 19000.0, "I", 0, 0, 2, 10, ec)
        be_E = BuildingElementOpaque(22.5, 135, 0.61, 0.50, 18000.0, "E", 180, 0, 2.25, 10, ec)
        be_IE = BuildingElementOpaque(25, 90, 0.62, 0.75, 17000.0, "IE", 90, 0, 2.5, 10, ec)
        be_D = BuildingElementOpaque(27.5, 45, 0.63, 0.80, 16000.0, "D", -90, 0, 2.75, 10, ec)
        be_M = BuildingElementOpaque(30, 0, 0.64, 0.40, 15000.0, "M", 0, 0, 3, 10, ec)

        # Put objects in a list that can be iterated over
        self.test_be_objs = [be_I, be_E, be_IE, be_D, be_M]

    def test_no_of_nodes(self):
        """ Test that number of nodes (total and inside) have been calculated correctly """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.no_of_nodes(), 5, "incorrect number of nodes")
                self.assertEqual(be.no_of_inside_nodes(), 3, "incorrect number of inside nodes")

    def test_area(self):
        """ Test that correct area is returned when queried """
        # Define increment between test cases
        area_inc = 2.5

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.area, 20.0 + i * area_inc, msg="incorrect area returned")

    def test_heat_flow_direction(self):
        """ Test that correct heat flow direction is returned when queried """
        temp_int_air = 20.0
        temp_int_surface = [19.0, 21.0, 22.0, 21.0, 19.0]
        results = [HeatFlowDirection.DOWNWARDS, HeatFlowDirection.UPWARDS, HeatFlowDirection.HORIZONTAL, HeatFlowDirection.DOWNWARDS, HeatFlowDirection.UPWARDS]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.heat_flow_direction(temp_int_air, temp_int_surface[i]),
                    results[i],
                    msg="incorrect heat flow direction returned"
                    )

    def test_r_si(self):
        """ Test that correct r_si is returned when queried """
        results = [0.17, 0.17, 0.13, 0.10, 0.10]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.r_si(),
                    results[i],
                    2,
                    msg="incorrect r_si returned"
                    )

    def test_h_ci(self):
        """ Test that correct h_ci is returned when queried """
        temp_int_air = 20.0
        temp_int_surface = [19.0, 21.0, 22.0, 21.0, 19.0]
        results = [0.7, 5.0, 2.5, 0.7, 5.0]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.h_ci(temp_int_air, temp_int_surface[i]),
                    results[i],
                    msg="incorrect h_ci returned"
                    )

    def test_h_ri(self):
        """ Test that correct h_ri is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ri(), 5.13, msg="incorrect h_ri returned")

    def test_h_ce(self):
        """ Test that correct h_ce is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ce(), 20.0, msg="incorrect h_ce returned")

    def test_h_re(self):
        """ Test that correct h_re is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_re(), 4.14, msg="incorrect h_re returned")

    def test_a_sol(self):
        """ Test that correct a_sol is returned when queried """
        # Define increment between test cases
        a_sol_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.a_sol, 0.6 + i * a_sol_inc, msg="incorrect a_sol returned")

    def test_therm_rad_to_sky(self):
        """ Test that correct therm_rad_to_sky is returned when queried """
        results = [0.0, 6.6691785923823135, 22.77, 38.87082140761768, 45.54]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.therm_rad_to_sky,
                    results[i],
                    msg="incorrect therm_rad_to_sky returned",
                    )

    def test_h_pli(self):
        """ Test that correct h_pli list is returned when queried """
        results = [
            [24.0, 12.0, 12.0, 24.0],
            [12.0, 6.0, 6.0, 12.0],
            [8.0, 4.0, 4.0, 8.0],
            [7.5, 3.75, 3.75, 7.5],
            [15.0, 7.5, 7.5, 15.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.h_pli, results[i], "incorrect h_pli list returned")

    def test_k_pli(self):
        """ Test that correct k_pli list is returned when queried """
        results = [
            [0.0, 0.0, 0.0, 0.0, 19000.0],
            [18000.0, 0.0, 0.0, 0.0, 0.0],
            [8500.0, 0.0, 0.0, 0.0, 8500.0],
            [2000.0, 4000.0, 4000.0, 4000.0, 2000.0],
            [0.0, 0.0, 15000.0, 0.0, 0.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.k_pli, results[i], "incorrect k_pli list returned")

    def test_temp_ext(self):
        """ Test that the correct external temperature is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            for t_idx, _, _ in self.simtime:
                with self.subTest(i = i * t_idx):
                    self.assertEqual(be.temp_ext(), t_idx * 5.0, "incorrect ext temp returned")

    def test_fabric_heat_loss(self):
        """ Test that the correct fabric heat loss is returned when queried """
        results = [43.20, 35.15, 27.10, 27.15, 55.54]

        for i, be in enumerate(self.test_be_objs):
            for t_idx, _, _ in self.simtime:
                with self.subTest(i = i):
                    self.assertAlmostEqual(be.fabric_heat_loss(),
                                            results[i],
                                            2,
                                            "incorrect fabric heat loss returned")

    def test_heat_capacity(self):
        """ Test that the correct heat capacity is returned when queried """
        results = [380, 405, 425, 440, 450]

        for i, be in enumerate(self.test_be_objs):
            for t_idx, _, _ in self.simtime:
                with self.subTest(i = i):
                    self.assertEqual(be.heat_capacity(),
                                            results[i],
                                            "incorrect heat capacity returned")

class TestBuildingElementAdjacentZTC(unittest.TestCase):
    """ Unit tests for BuildingElementAdjacentZTC class """

    def setUp(self):
        """ Create BuildingElementAdjacentZTC objects to be tested """
        self.simtime = SimulationTime(0, 4, 1)
        ec = ExternalConditions(self.simtime,
                                [0.0, 5.0, 10.0, 15.0],
                                None,
                                [0.0] * 4, # Diffuse horizontal radiation
                                [0.0] * 4, # Direct beam radiation
                                None,
                                55.0, # Latitude
                                0.0, # Longitude
                                0.0, # Timezone
                                0, # Start day
                                None,
                                1, # Time-series step
                                None,
                                None,
                                None,
                                None,
                                None
                                )
        # Create an object for each mass distribution class
        be_I = BuildingElementAdjacentZTC(20.0, 180, 0.25, 19000.0, "I", ec)
        be_E = BuildingElementAdjacentZTC(22.5, 135, 0.50, 18000.0, "E", ec)
        be_IE = BuildingElementAdjacentZTC(25.0, 90, 0.75, 17000.0, "IE", ec)
        be_D = BuildingElementAdjacentZTC(27.5, 45, 0.80, 16000.0, "D", ec)
        be_M = BuildingElementAdjacentZTC(30.0, 0, 0.40, 15000.0, "M", ec)

        # Put objects in a list that can be iterated over
        self.test_be_objs = [be_I, be_E, be_IE, be_D, be_M]

    def test_no_of_nodes(self):
        """ Test that number of nodes (total and inside) have been calculated correctly """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.no_of_nodes(), 5, "incorrect number of nodes")
                self.assertEqual(be.no_of_inside_nodes(), 3, "incorrect number of inside nodes")

    def test_area(self):
        """ Test that correct area is returned when queried """
        # Define increment between test cases
        area_inc = 2.5

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.area, 20.0 + i * area_inc, msg="incorrect area returned")

    def test_heat_flow_direction(self):
        """ Test that correct heat flow direction is returned when queried """
        temp_int_air = 20.0
        temp_int_surface = [19.0, 21.0, 22.0, 21.0, 19.0]
        results = [HeatFlowDirection.DOWNWARDS, HeatFlowDirection.UPWARDS, HeatFlowDirection.HORIZONTAL, HeatFlowDirection.DOWNWARDS, HeatFlowDirection.UPWARDS]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.heat_flow_direction(temp_int_air, temp_int_surface[i]),
                    results[i],
                    msg="incorrect heat flow direction returned"
                    )

    def test_r_si(self):
        """ Test that correct r_si is returned when queried """
        results = [0.17, 0.17, 0.13, 0.10, 0.10]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.r_si(),
                    results[i],
                    2,
                    msg="incorrect r_si returned"
                    )

    def test_h_ci(self):
        """ Test that correct h_ci is returned when queried """
        temp_int_air = 20.0
        temp_int_surface = [19.0, 21.0, 22.0, 21.0, 19.0]
        results = [0.7, 5.0, 2.5, 0.7, 5.0]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.h_ci(temp_int_air, temp_int_surface[i]),
                    results[i],
                    msg="incorrect h_ci returned"
                    )

    def test_h_ri(self):
        """ Test that correct h_ri is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ri(), 5.13, msg="incorrect h_ri returned")

    def test_h_ce(self):
        """ Test that correct h_ce is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ce(), 0.0, msg="incorrect h_ce returned")

    def test_h_re(self):
        """ Test that correct h_re is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_re(), 0.0, msg="incorrect h_re returned")

    def test_a_sol(self):
        """ Test that correct a_sol is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.a_sol, 0.0, msg="incorrect a_sol returned")

    def test_therm_rad_to_sky(self):
        """ Test that correct therm_rad_to_sky is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.therm_rad_to_sky,
                    0.0,
                    msg="incorrect therm_rad_to_sky returned",
                    )

    def test_h_pli(self):
        """ Test that correct h_pli list is returned when queried """
        results = [
            [24.0, 12.0, 12.0, 24.0],
            [12.0, 6.0, 6.0, 12.0],
            [8.0, 4.0, 4.0, 8.0],
            [7.5, 3.75, 3.75, 7.5],
            [15.0, 7.5, 7.5, 15.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.h_pli, results[i], "incorrect h_pli list returned")

    def test_k_pli(self):
        """ Test that correct k_pli list is returned when queried """
        results = [
            [0.0, 0.0, 0.0, 0.0, 19000.0],
            [18000.0, 0.0, 0.0, 0.0, 0.0],
            [8500.0, 0.0, 0.0, 0.0, 8500.0],
            [2000.0, 4000.0, 4000.0, 4000.0, 2000.0],
            [0.0, 0.0, 15000.0, 0.0, 0.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.k_pli, results[i], "incorrect k_pli list returned")

    # No test for temp_ext - not relevant as the external wall bounds ZTC not the external environment

    def test_fabric_heat_loss(self):
        """ Test that the correct fabric heat loss is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            for t_idx, _, _ in self.simtime:
                with self.subTest(i = i):
                    self.assertEqual(be.fabric_heat_loss(),
                                            0.0,
                                            "incorrect fabric heat loss returned")

    def test_heat_capacity(self):
        """ Test that the correct heat capacity is returned when queried """
        results = [380, 405, 425, 440, 450]

        for i, be in enumerate(self.test_be_objs):
            for t_idx, _, _ in self.simtime:
                with self.subTest(i = i):
                    self.assertEqual(be.heat_capacity(),
                                            results[i],
                                            "incorrect heat capacity returned")

class TestBuildingElementGround(unittest.TestCase):
    """ Unit tests for BuildingElementGround class """

    def setUp(self):
        """ Create BuildingElementGround objects to be tested """
        self.simtime = SimulationTime(742, 746, 1)

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

        airtemp = []
        airtemp.extend(air_temp_day_Jan * 31)
        airtemp.extend(air_temp_day_Feb * 28)
        airtemp.extend(air_temp_day_Mar * 31)
        airtemp.extend(air_temp_day_Apr * 30)
        airtemp.extend(air_temp_day_May * 31)
        airtemp.extend(air_temp_day_Jun * 30)
        airtemp.extend(air_temp_day_Jul * 31)
        airtemp.extend(air_temp_day_Aug * 31)
        airtemp.extend(air_temp_day_Sep * 30)
        airtemp.extend(air_temp_day_Oct * 31)
        airtemp.extend(air_temp_day_Nov * 30)
        airtemp.extend(air_temp_day_Dec * 31)

        ec = ExternalConditions(self.simtime,
                                airtemp,
                                None,
                                [0.0] * 8760, # Diffuse horizontal radiation
                                [0.0] * 8760, # Direct beam radiation
                                None,
                                55.0, # Latitude
                                0.0, # Longitude
                                0.0, # Timezone
                                0, # Start day
                                None,
                                1, # Time-series step
                                None,
                                None,
                                None,
                                None,
                                None
                                )
        #TODO implement rest of external conditions in unit tests

        # Create an object for each mass distribution class
        be_I = BuildingElementGround(20.0, 180, 1.5, 0.1, 19000.0, "I", 2.0, 2.5, 18.0, 0.5, ec, self.simtime)
        be_E = BuildingElementGround(22.5, 135, 1.4, 0.2, 18000.0, "E", 2.1, 2.6, 19.0, 0.6, ec, self.simtime)
        be_IE = BuildingElementGround(25.0, 90, 1.33, 0.2, 17000.0, "IE", 2.2, 2.7, 20.0, 0.7, ec, self.simtime)
        be_D = BuildingElementGround(27.5, 45, 1.25, 0.2, 16000.0, "D", 2.3, 2.8, 21.0, 0.8, ec, self.simtime)
        be_M = BuildingElementGround(30.0, 0, 1.0, 0.3, 15000.0, "M", 2.4, 2.9, 22.0, 0.9, ec, self.simtime)

        # Put objects in a list that can be iterated over
        self.test_be_objs = [be_I, be_E, be_IE, be_D, be_M]

    def test_no_of_nodes(self):
        """ Test that number of nodes (total and inside) have been calculated correctly """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.no_of_nodes(), 5, "incorrect number of nodes")
                self.assertEqual(be.no_of_inside_nodes(), 3, "incorrect number of inside nodes")

    def test_area(self):
        """ Test that correct area is returned when queried """
        # Define increment between test cases
        area_inc = 2.5

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.area, 20.0 + i * area_inc, msg="incorrect area returned")

    def test_heat_flow_direction(self):
        """ Test that correct heat flow direction is returned when queried """
        temp_int_air = 20.0
        temp_int_surface = [19.0, 21.0, 22.0, 21.0, 19.0]
        results = [HeatFlowDirection.DOWNWARDS, HeatFlowDirection.UPWARDS, HeatFlowDirection.HORIZONTAL, HeatFlowDirection.DOWNWARDS, HeatFlowDirection.UPWARDS]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.heat_flow_direction(temp_int_air, temp_int_surface[i]),
                    results[i],
                    msg="incorrect heat flow direction returned"
                    )

    def test_r_si(self):
        """ Test that correct r_si is returned when queried """
        results = [0.17, 0.17, 0.13, 0.10, 0.10]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.r_si(),
                    results[i],
                    2,
                    msg="incorrect r_si returned"
                    )

    def test_h_ci(self):
        """ Test that correct h_ci is returned when queried """
        temp_int_air = 20.0
        temp_int_surface = [19.0, 21.0, 22.0, 21.0, 19.0]
        results = [0.7, 5.0, 2.5, 0.7, 5.0]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.h_ci(temp_int_air, temp_int_surface[i]),
                    results[i],
                    msg="incorrect h_ci returned"
                    )

    def test_h_ri(self):
        """ Test that correct h_ri is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ri(), 5.13, msg="incorrect h_ri returned")

    def test_h_ce(self):
        """ Test that correct h_ce is returned when queried """
        results = [15.78947368, 91.30434783, 20.59886422, 10.34482759, 5.084745763]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ce(), results[i], msg="incorrect h_ce returned")

    def test_h_re(self):
        """ Test that correct h_re is returned when queried """
        # Define increment between test cases
        h_re_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_re(), 0.0, msg="incorrect h_re returned")

    def test_a_sol(self):
        """ Test that correct a_sol is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.a_sol, 0.0, msg="incorrect a_sol returned")

    def test_therm_rad_to_sky(self):
        """ Test that correct therm_rad_to_sky is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.therm_rad_to_sky,
                    0.0,
                    msg="incorrect therm_rad_to_sky returned",
                    )

    def test_h_pli(self):
        """ Test that correct h_pli list is returned when queried """
        results = [
            [6.0, 3.0, 3.0, 6.0],
            [6.0, 2.896551724137931, 2.8, 5.6],
            [6.0, 2.8197879858657244, 2.66, 5.32],
            [6.0, 2.727272727272727, 2.5, 5.0],
            [6.0, 2.4000000000000004, 2.0, 4.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.h_pli, results[i], "incorrect h_pli list returned")

    def test_k_pli(self):
        """ Test that correct k_pli list is returned when queried """
        results = [
            [0.0, 1500000.0, 0.0, 0.0, 19000.0],
            [0.0, 1500000.0, 18000.0, 0.0, 0.0],
            [0.0, 1500000.0, 8500.0, 0.0, 8500.0],
            [0.0, 1500000.0, 4000.0, 8000.0, 4000.0],
            [0.0, 1500000.0, 0.0, 15000.0, 0.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.k_pli, results[i], "incorrect k_pli list returned")

    def test_temp_ext(self):
        """ Test that the correct external temperature is returned when queried """
        results = [8.474795225438358, 8.474795225438358, 8.988219392771693, 8.988219392771693]

        for i, be in enumerate(self.test_be_objs):
            for t_idx, _, _ in self.simtime:
                with self.subTest(i = i * t_idx):
                    self.assertEqual(be.temp_ext(), results[t_idx], "incorrect ext temp returned")

    def test_fabric_heat_loss(self):
        """ Test that the correct fabric heat loss is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i = i):
                self.assertAlmostEqual(be.fabric_heat_loss(),
                                        [30.0, 31.5, 33.25, 34.375, 30.0][i],
                                        2,
                                        "incorrect fabric heat loss returned")

    def test_heat_capacity(self):
        """ Test that the correct heat capacity is returned when queried """
        results = [380, 405, 425, 440, 450]

        for i, be in enumerate(self.test_be_objs):
            for t_idx, _, _ in self.simtime:
                with self.subTest(i = i):
                    self.assertEqual(be.heat_capacity(),
                                            results[i],
                                            "incorrect heat capacity returned")

class TestBuildingElementTransparent(unittest.TestCase):
    """ Unit tests for BuildingElementTransparent class """

    def setUp(self):
        """ Create BuildingElementTransparent object to be tested """
        self.simtime = SimulationTime(0, 4, 1)
        ec = ExternalConditions(self.simtime,
                                [0.0, 5.0, 10.0, 15.0],
                                None,
                                [0.0] * 4, # Diffuse horizontal radiation
                                [0.0] * 4, # Direct beam radiation
                                None,
                                55.0, # Latitude
                                0.0, # Longitude
                                0.0, # Timezone
                                0, # Start day
                                None,
                                1, # Time-series step
                                None,
                                None,
                                None,
                                None,
                                None
                                )
        #TODO implement rest of external conditions in unit tests

        self.be = BuildingElementTransparent(90, 0.4, 180, 0.75, 0.25, 1, 1.25, 4, False, ec)

    def test_no_of_nodes(self):
        """ Test that number of nodes (total and inside) have been calculated correctly """
        self.assertEqual(self.be.no_of_nodes(), 2, "incorrect number of nodes")
        self.assertEqual(self.be.no_of_inside_nodes(), 0, "incorrect number of inside nodes")

    def test_area(self):
        """ Test that correct area is returned when queried """
        self.assertEqual(self.be.area, 5.0, "incorrect area returned")

    def test_heat_flow_direction(self):
        """ Test that correct heat flow direction is returned when queried """
        self.assertEqual(self.be.heat_flow_direction(None, None), HeatFlowDirection.HORIZONTAL, "incorrect heat flow direction returned")

    def test_r_si(self):
        """ Test that correct r_si is returned when queried """
        self.assertAlmostEqual(self.be.r_si(), 0.13, 2, "incorrect r_si returned")

    def test_h_ci(self):
        """ Test that correct h_ci is returned when queried """
        self.assertEqual(self.be.h_ci(None, None), 2.5, "incorrect h_ci returned")

    def test_h_ri(self):
        """ Test that correct h_ri is returned when queried """
        self.assertEqual(self.be.h_ri(), 5.13, "incorrect h_ri returned")

    def test_h_ce(self):
        """ Test that correct h_ce is returned when queried """
        self.assertEqual(self.be.h_ce(), 20.0, "incorrect h_ce returned")

    def test_h_re(self):
        """ Test that correct h_re is returned when queried """
        self.assertEqual(self.be.h_re(), 4.14, "incorrect h_re returned")

    def test_a_sol(self):
        """ Test that correct a_sol is returned when queried """
        self.assertEqual(self.be.a_sol, 0.0, "non-zero a_sol returned")

    def test_therm_rad_to_sky(self):
        """ Test that correct therm_rad_to_sky is returned when queried """
        self.assertEqual(self.be.therm_rad_to_sky, 22.77, "incorrect therm_rad_to_sky returned")

    def test_h_pli(self):
        """ Test that correct h_pli list is returned when queried """
        self.assertEqual(self.be.h_pli, [2.5], "incorrect h_pli list returned")

    def test_k_pli(self):
        """ Test that correct k_pli list is returned when queried """
        self.assertEqual(self.be.k_pli, [0.0, 0.0], "non-zero k_pli list returned")

    def test_temp_ext(self):
        """ Test that the correct external temperature is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertEqual(
                    self.be.temp_ext(),
                    t_idx * 5.0,
                    "incorrect ext temp returned",
                    )

    def test_fabric_heat_loss(self):
        """ Test that correct fabric heat loss is returned when queried """
        self.assertAlmostEqual(self.be.fabric_heat_loss(),
                               8.16,
                               2,
                               "incorrect fabric heat loss returned")

    def test_heat_capacity(self):
        """ Test that the correct heat capacity is returned when queried """
        self.assertEqual(self.be.heat_capacity(),
                                0,
                                "incorrect heat capacity returned")
