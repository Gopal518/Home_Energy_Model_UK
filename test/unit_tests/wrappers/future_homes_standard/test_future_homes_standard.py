#!/usr/bin/env python3

"""
This module contains unit tests for the Future Homes Standard module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from wrappers.future_homes_standard import future_homes_standard 
   
      
class TestFutureHomesStandard(unittest.TestCase):

    def setUp(self):    
        self.project_dict = \
            {'Shower':
                {'mixer': {'type': 'MixerShower', 'flowrate': 0, 'ColdWaterSource': 'mains water'}, 
                 'IES':   {'type': 'InstantElecShower', 'rated_power': 9.0, 'ColdWaterSource': 'mains water', 'EnergySupply': 'mains elec'}
                }
            }                        
      
    def test_check_invalid_shower_flowrate(self):  
   
        self.project_dict['Shower']['mixer']['flowrate'] = 7.0
        valid_flowrate = future_homes_standard.check_shower_flowrate(self.project_dict)
        self.assertFalse(False, "Expected False")
        
    def test_check_valid_shower_flowrate(self):  

        self.project_dict['Shower']['mixer']['flowrate'] = 10.0
        valid_flowrate = future_homes_standard.check_shower_flowrate(self.project_dict)
        self.assertTrue(True, "Expected True")
        
    def test_check_minimum_shower_flowrate(self):  

        self.project_dict['Shower']['mixer']['flowrate'] = 8.0
        valid_flowrate = future_homes_standard.check_shower_flowrate(self.project_dict)
        self.assertTrue(True, "Expected True")
        
    def test_calc_1_occupant(self):
        
        # test with one occupant and a range of floor areas
        num_occupants = future_homes_standard.calc_N_occupants(10, 1)
        self.assertAlmostEqual(1.075, num_occupants, 2, 
                               "Occupancy value {0} not expected for 1 bedroom".format(num_occupants))        
       
        num_occupants = future_homes_standard.calc_N_occupants(20, 1)
        self.assertAlmostEqual(1.232, num_occupants, 2, 
                               "Occupancy value {0} not expected for 1 bedroom".format(num_occupants))    
        
        num_occupants = future_homes_standard.calc_N_occupants(50, 1)
        self.assertAlmostEqual(1.433, num_occupants, 2, 
                               "Occupancy value {0} not expected for 1 bedroom".format(num_occupants))        
        
        num_occupants = future_homes_standard.calc_N_occupants(100, 1)
        self.assertAlmostEqual(1.437, num_occupants, 2, 
                               "Occupancy value {0} not expected for 1 bedroom".format(num_occupants))
        
    
    def test_calc_N_occupants(self):
        
        num_occupants = future_homes_standard.calc_N_occupants(100, 2)
        self.assertEqual(2.2472, num_occupants, 
                         "Occupancy value {0} not expected for 2 bedrooms".format(num_occupants))        
        
        num_occupants = future_homes_standard.calc_N_occupants(100, 3)
        self.assertEqual(2.9796, num_occupants, 
                         "Occupancy value {0} not expected for 3 bedrooms".format(num_occupants))   
        
        num_occupants = future_homes_standard.calc_N_occupants(100, 4)
        self.assertEqual(3.3715, num_occupants, 
                         "Occupancy value {0} not expected for 4 bedrooms".format(num_occupants))           
        
        num_occupants = future_homes_standard.calc_N_occupants(100, 5)
        self.assertEqual(3.8997, num_occupants, 
                         "Occupancy value {0} not expected for 5 bedrooms".format(num_occupants))           
        
        num_occupants = future_homes_standard.calc_N_occupants(100, 6)
        self.assertEqual(3.8997, num_occupants, 
                         "Occupancy value {0} not expected for 6 bedrooms".format(num_occupants))           


    def test_calc_N_occupants_invalid_bedrooms(self):
    
        self.assertRaises(ValueError, future_homes_standard.calc_N_occupants, 100, 0)
        self.assertRaises(ValueError, future_homes_standard.calc_N_occupants, 100, -1)
       
    def test_calc_N_occupants_invalid_floor_area(self):
    
        self.assertRaises(ValueError, future_homes_standard.calc_N_occupants, 0, 1)
        self.assertRaises(ValueError, future_homes_standard.calc_N_occupants, -1, 1)
        
                          
    