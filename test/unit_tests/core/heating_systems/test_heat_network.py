#!/usr/bin/env python3

"""
This module contains unit tests for the heat network module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.external_conditions import ExternalConditions
from core.controls.time_control import SetpointTimeControl
from core.heating_systems.heat_network import HeatNetwork, HeatNetworkServiceWaterDirect, \
HeatNetworkServiceWaterStorage, HeatNetworkServiceSpace
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.energy_supply.energy_supply import EnergySupply
from core.material_properties import WATER, MaterialProperties


class TestHeatNetwork(unittest.TestCase):
    """ Unit tests for HeatNetwork class """

    def setUp(self):
        """ Create HeatNetwork object to be tested """
        self.simtime = SimulationTime(0, 2, 1)
        self.energysupply = EnergySupply("custom", self.simtime)
        energy_supply_conn_name_auxiliary = 'heat_network_auxiliary'
        energy_supply_conn_name_building_level_distribution_losses \
                    = 'HeatNetwork_building_level_distribution_losses'

        # Set up HeatNetwork object
        self.heat_network = HeatNetwork(
            6.0, # power_max
            0.24, # HIU daily loss
            0.8, # Building level distribution losses
            self.energysupply,
            energy_supply_conn_name_auxiliary,
            energy_supply_conn_name_building_level_distribution_losses,
            self.simtime,
            )

        # Create a service connection
        self.heat_network._HeatNetwork__create_service_connection("heat_network_test")

    def test_energy_output_provided(self):
        """ Test that HeatNetwork object returns correct energy and fuel demand """
        energy_output_required = [2.0, 10.0]
        temp_return = [50.0, 60.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network._HeatNetwork__demand_energy(
                                        "heat_network_test",
                                        energy_output_required[t_idx],
                                        ),
                    [2.0, 6.0][t_idx],
                    msg="incorrect energy_output_provided"
                    )
                self.heat_network.timestep_end()

                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()["heat_network_test"][t_idx],
                    [2.0, 6.0][t_idx],
                    msg="incorrect fuel demand"
                    )
                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()["heat_network_auxiliary"][t_idx],
                    [0.01, 0.01][t_idx],
                    msg="incorrect fuel demand"
                    )

    def test_HIU_loss(self):
        """ Test that HeatNetwork object returns correct HIU loss """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network.HIU_loss(),
                    0.01,
                    msg="incorrect HIU loss returned"
                    )

    def test_building_level_distribution_losses(self):
        """ Test that HeatNetwork object returns correct building level distribution loss """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network.building_level_loss(),
                    0.0008,
                    msg="incorrect building level distribution losses returned"
                    )

class TestHeatNetworkServiceWaterDirect(unittest.TestCase):
    """ Unit tests for HeatNetworkServiceWaterDirect class """

    def setUp(self):
        """ Create HeatNetworkServiceWaterDirect object to be tested """
        heat_network_dict = {"type": "HeatNetwork",
                             "EnergySupply": "custom"
                             }
        self.simtime = SimulationTime(0, 2, 1)
        self.energysupply = EnergySupply("custom", self.simtime)
        self.energy_output_required = [2.0, 10.0]
        self.temp_return_feed = [51.05, 60.00]
        energy_supply_conn_name_auxiliary = 'heat_network_auxiliary'
        energy_supply_conn_name_building_level_distribution_losses \
                    = 'HeatNetwork_building_level_distribution_losses'

        # Set up HeatNetwork
        self.heat_network = HeatNetwork(
            18.0, # power_max
            1.0, # HIU daily loss
            0.8, # Building level distribution loss 
            self.energysupply,
            energy_supply_conn_name_auxiliary,
            energy_supply_conn_name_building_level_distribution_losses,
            self.simtime,
            )

        self.heat_network._HeatNetwork__create_service_connection("heat_network_test")

        # Set up HeatNetworkServiceWaterDirect
        coldwatertemps = [1.0, 1.2]
        coldfeed = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        return_temp = 60
        self.heat_network_service_water_direct = HeatNetworkServiceWaterDirect(
            self.heat_network,
            "heat_network_test", 
            return_temp,
            coldfeed,
            self.simtime
            )

    def test_heat_network_service_water(self):
        """ Test that HeatNetwork object returns correct hot water energy demand """
        volume_demanded = [50.0, 100.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network_service_water_direct.demand_hot_water(volume_demanded[t_idx]),
                    [3.429, 6.834][t_idx],
                    3,
                    msg="incorrect energy_output_provided"
                    )
            self.heat_network.timestep_end()


class TestHeatNetworkServiceWaterStorage(unittest.TestCase):
    """ Unit tests for HeatNetworkServiceWaterStorage class """

    def setUp(self):
        """ Create HeatNetworkServiceWaterStorage object to be tested """
        self.simtime = SimulationTime(0, 2, 1)
        self.energysupply = EnergySupply("custom", self.simtime)
        self.energy_output_required = [2.0, 10.0]
        self.temp_return_feed = [51.05, 60.00]
        energy_supply_conn_name_auxiliary = 'heat_network_auxiliary'
        energy_supply_conn_name_building_level_distribution_losses \
                    = 'HeatNetwork_building_level_distribution_losses'

        # Set up HeatNetwork
        self.heat_network = HeatNetwork(
            7.0, # power_max
            1.0, # HIU daily loss
            0.8, # Building level distribution loss 
            self.energysupply,
            energy_supply_conn_name_auxiliary,
            energy_supply_conn_name_building_level_distribution_losses,
            self.simtime,
            )

        self.heat_network._HeatNetwork__create_service_connection("heat_network_test")

        # Set up HeatNetworkServiceWaterStorage
        coldwatertemps = [1.0, 1.2]
        coldfeed = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        self.heat_network_service_water_storage= HeatNetworkServiceWaterStorage(
            self.heat_network,
            "heat_network_test",
            60, # temp_hot_water
            )

    def test_heat_network_service_water_storage(self):
        """ Test that HeatNetwork object returns correct energy demand for the storage tank """
        # TODO update results
        energy_demanded = [10.0, 2.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network_service_water_storage.demand_energy(energy_demanded[t_idx]),
                    [7.0, 2.0][t_idx],
                    msg="incorrect energy_output_provided"
                    )
            self.heat_network.timestep_end()


class TestHeatNetworkServiceSpace(unittest.TestCase):
    """ Unit tests for HeatNetworkServiceSpace class """

    def setUp(self):
        """ Create HeatNetworkServiceSpace object to be tested """
        self.simtime = SimulationTime(0, 3, 1)
        self.energysupply = EnergySupply("mains_gas", self.simtime)
        energy_supply_conn_name_auxiliary = 'Boiler_auxiliary'
        energy_supply_conn_name_building_level_distribution_losses \
                    = 'HeatNetwork_building_level_distribution_losses'

        # Set up HeatNetwork
        self.heat_network = HeatNetwork(
            5.0, # power_max
            1.0, # HIU daily loss
            0.8, # Building level distribution loss 
            self.energysupply,
            energy_supply_conn_name_auxiliary,
            energy_supply_conn_name_building_level_distribution_losses,
            self.simtime,
            )

        self.heat_network._HeatNetwork__create_service_connection("heat_network_test")

        # Set up HeatNetworkServiceSpace
        ctrl = SetpointTimeControl(
            [21.0, 21.0, None],
            self.simtime,
            0, #start_day
            1.0, #time_series_step
            )
        self.heat_network_service_space = HeatNetworkServiceSpace(
            self.heat_network,
            "heat_network_test",
            ctrl,
            )

    def test_heat_network_service_space(self):
        """ Test that HeatNetworkServiceSpace object returns correct space heating energy demand """
        energy_demanded = [10.0, 2.0, 2.0]
        temp_flow = [55.0, 65.0, 65.0]
        temp_return = [50.0, 60.0, 60.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network_service_space.demand_energy(
                        energy_demanded[t_idx],
                        temp_flow[t_idx],
                        temp_return[t_idx]),
                    [5.0, 2.0, 0.0][t_idx],
                    msg="incorrect energy_output_provided"
                    )
            self.heat_network.timestep_end()

