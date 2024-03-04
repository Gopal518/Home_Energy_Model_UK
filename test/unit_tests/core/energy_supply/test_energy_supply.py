#!/usr/bin/env python3

"""
This module contains unit tests for the energy_supply module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.energy_supply.energy_supply import EnergySupply, EnergySupplyConnection

class TestEnergySupply(unittest.TestCase):
    """ Unit tests for EnergySupply class """

    def setUp(self):
        """ Create EnergySupply object to be tested """
        self.simtime            = SimulationTime(0, 8, 1)
        self.energysupply       = EnergySupply("mains_gas", self.simtime)
        """ Set up two different energy supply connections """
        self.energysupplyconn_1 = self.energysupply.connection("shower")
        self.energysupplyconn_2 = self.energysupply.connection("bath")

    def test_connection(self):
        """ Test the correct end user name is assigned when creating the
        two different connections.
        """
        self.assertEqual(
            self.energysupplyconn_1._EnergySupplyConnection__end_user_name,
            "shower",
            "end user name for connection 1 not returned"
            )
        self.assertEqual(
            self.energysupplyconn_2._EnergySupplyConnection__end_user_name,
            "bath",
            "end user name for connection 2 not returned"
            )

        """ Test the energy supply is created as expected for the two
        different connections.
        """
        self.assertIs(
            self.energysupply,
            self.energysupplyconn_1._EnergySupplyConnection__energy_supply,
            "energy supply for connection 1 not returned"
            )
        self.assertIs(
            self.energysupply,
            self.energysupplyconn_2._EnergySupplyConnection__energy_supply,
            "energy supply for connection 2 not returned"
            )

    def test_results_total(self):
        """ Check the correct list of the total demand on this energy
        source for each timestep is returned.
        """
        demandtotal = [50.0, 120.0, 190.0, 260.0, 330.0, 400.0, 470.0, 540.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.energysupplyconn_1.demand_energy((t_idx+1.0)*50.0)
                self.energysupplyconn_2.demand_energy((t_idx)*20.0)
                self.assertEqual(
                    self.energysupply.results_total()[t_idx],
                    demandtotal[t_idx],
                    "incorrect total demand energy returned",
                    )

    def test_results_by_end_user(self):
        """ Check the correct list of the total demand on this energy
        source for each timestep is returned for each connection.
        """
        demandtotal_1 = [50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0]
        demandtotal_2 = [0.0, 20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.energysupplyconn_1.demand_energy((t_idx+1.0)*50.0)
                self.energysupplyconn_2.demand_energy((t_idx)*20.0)
                self.assertEqual(
                    self.energysupply.results_by_end_user()["shower"][t_idx],
                    demandtotal_1[t_idx],
                    "incorrect demand by end user returned",
                    )
                self.assertEqual(
                    self.energysupply.results_by_end_user()["bath"][t_idx],
                    demandtotal_2[t_idx],
                    "incorrect demand by end user returned",
                    )

    def test_beta_factor(self):
        """check beta factor and surplus supply/demand are calculated correctly"""
        energysupplyconn_3 = self.energysupply.connection("PV")
        betafactor = [1.0, 
                      0.8973610789278808, 
                      0.4677549807236648, 
                      0.3297589507351858, 
                      0.2578125, 
                      0.2, 
                      0.16319444444444445, 
                      0.1377551020408163]
        
        surplus = [0.0, -8.21111368576954, -170.3184061684273, -482.57355547066624, -950.0, -1600.0, -2410.0, -3380.0]
        demandnotmet = [50.0, 48.21111368576953, 40.31840616842726, 22.573555470666236, 0.0, 0.0, 0.0, 0.0]

        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.energysupplyconn_1.demand_energy((t_idx+1.0)*50.0)
                self.energysupplyconn_2.demand_energy((t_idx)*20.0)
                energysupplyconn_3.supply_energy((t_idx)*(t_idx)*80.0)
                
                self.energysupply.calc_energy_import_export_betafactor()
    
                self.assertEqual(
                    self.energysupply.get_beta_factor()[t_idx],
                    betafactor[t_idx],
                    "incorrect beta factor returned",
                    )
                self.assertEqual(
                    self.energysupply.get_energy_export()[t_idx],
                    surplus[t_idx],
                    "incorrect energy export returned",
                    )
                self.assertEqual(
                    self.energysupply.get_energy_import()[t_idx],
                    demandnotmet[t_idx],
                    "incorrect energy import returned",
                    )
    