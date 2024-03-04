#!/usr/bin/env python3

"""
This module provides object(s) to model the behaviour of point of use heaters
"""

import core.water_heat_demand.misc as misc


class PointOfUse:
    """ Class to represent point of use water heaters """

    def __init__(
            self,
            rated_power,
            efficiency,
            energy_supply_conn,
            simulation_time,
            cold_feed
            ):
        """ Construct an InstantElecHeater object

        Arguments:
        rated_power        -- in kW
        efficiency         -- efficiency of the heater, between 0 and 1
        energy_supply_conn -- reference to EnergySupplyConnection object
        simulation_time    -- reference to SimulationTime object
        cold_feed            -- reference to ColdWaterSource object
        """
        self.__pwr                = rated_power
        self.__efficiency         = efficiency
        self.__energy_supply_conn = energy_supply_conn
        self.__simulation_time    = simulation_time
        self.__cold_feed          = cold_feed

    def get_cold_water_source(self):
        return self.__cold_feed

    def demand_hot_water(self, volume_demanded):
        demand_temp = 52
        # TODO set required temperature rather than hard coding - also elsewhere in the code
        
        water_energy_demand = misc.water_demand_to_kWh(volume_demanded, demand_temp, self.__cold_feed.temperature())
        
        energy_used = self.demand_energy(water_energy_demand)

        # Assumption is that system specified has sufficient capacity to meet any realistic demand
        return energy_used

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the heater """
        # Energy that heater is able to supply is limited by power rating
        fuel_demand = min(energy_demand, self.__pwr * self.__simulation_time.timestep()) * (1/self.__efficiency)

        self.__energy_supply_conn.demand_energy(fuel_demand)
        return fuel_demand
