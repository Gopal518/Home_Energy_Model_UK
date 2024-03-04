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
    BuildingElementAdjacentZTC, BuildingElementAdjacentZTU_Simple
from core.space_heat_demand.zone import Zone
from core.space_heat_demand.thermal_bridge import ThermalBridgeLinear, ThermalBridgePoint
from core.space_heat_demand.ventilation_element import VentilationElementInfiltration

class TestZone(unittest.TestCase):
    """ Unit tests for Zone class """

    def setUp(self):
        """ Create Zone object to be tested """
        self.simtime = SimulationTime(0, 4, 1)

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

        ec = ExternalConditions(self.simtime,
                                self.airtemp,
                                self.windspeed,
                                [0.0] * 4, # Diffuse horizontal radiation
                                [0.0] * 4, # Direct beam radiation
                                [0.2] * 4,
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

        # Create objects for the different building elements in the zone
        be_opaque_I = BuildingElementOpaque(20, 180, 0.60, 0.25, 19000.0, "I", 0, 0, 2, 10, ec)
        be_opaque_D = BuildingElementOpaque(26, 180, 0.55, 0.33, 16000.0, "D", 0, 0, 2, 10, ec)
        be_ZTC = BuildingElementAdjacentZTC(22.5, 135, 0.50, 18000.0, "E", ec)
        be_ground = BuildingElementGround(25.0, 90, 1.33, 0.2, 17000.0, "IE", 2.2, 2.7, 20.0, 0.7, ec, self.simtime)
        be_transparent = BuildingElementTransparent(90, 0.4, 180, 0.75, 0.25, 1, 1.25, 4, False, ec)
        be_ZTU = BuildingElementAdjacentZTU_Simple(30, 130, 0.50, 0.6, 18000.0, "E", ec)

        # Put building element objects in a list that can be iterated over
        be_objs = [be_opaque_I, be_opaque_D, be_ZTC, be_ground, be_transparent, be_ZTU]

        # Create objects for thermal bridges
        tb_linear_1 = ThermalBridgeLinear(0.28, 5.0)
        tb_linear_2 = ThermalBridgeLinear(0.25, 6.0)
        tb_point = ThermalBridgePoint(1.4)

        # Put thermal bridge objects in a list that can be iterated over
        tb_objs = [tb_linear_1, tb_linear_2, tb_point]

        # Create ventilation objects
        ve = VentilationElementInfiltration(1.0, 
                                            "sheltered",
                                            "house",
                                            4.5,
                                            "50Pa",
                                            40.0,
                                            75.0,
                                            2.0,
                                            2.0,
                                            2.0,
                                            1.0,
                                            0.0,
                                            0.0,
                                            0.0,
                                            3.0,
                                            6.0,
                                            0.0,
                                            ec)

        # Put thermal ventilation objects in a list that can be iterated over
        ve_objs = [ve]
        
        temp_ext_air_init = 17
        temp_setpnt_init = 21
        
        self.zone = Zone(50.0,
                         125.0,
                         be_objs,
                         tb_objs,
                         ve_objs,
                         temp_ext_air_init,
                         temp_setpnt_init)

    def test_volume(self):
        """ Test that the correct volume is returned when queried """
        self.assertEqual(
            self.zone.volume(),
            125.0,
            "incorrect volume returned"
            )

    def test_total_fabric_heat_loss(self):
        """ Test that the correct total for fabric heat loss is returned when queried """
        temp_int_air = 20.0
        temp_int_surface = 19.0

        self.assertAlmostEqual(self.zone.total_fabric_heat_loss(),
                               174.58,
                               2,
                               "incorrect total fabric heat loss returned")

    def test_total_heat_capacity(self):
        """ Test that the correct total for heat capacity is returned when queried """
        self.assertEqual(self.zone.total_heat_capacity(),
                               2166,
                               "incorrect total heat capacity returned")

    def test_total_thermal_bridges(self):
        """ Test that the correct total for thermal bridges is returned when queried """
        self.assertAlmostEqual(self.zone.total_thermal_bridges(),
                               4.3,
                               2,
                               "incorrect thermal bridge total returned")

    def test_total_vent_heat_loss(self):
        """ Test that the correct total for ventilation heat loss is returned when queried """
        self.assertAlmostEqual(self.zone.total_vent_heat_loss(),
                               157.9,
                               1,
                               "incorrect total ventilation heat loss returned")
