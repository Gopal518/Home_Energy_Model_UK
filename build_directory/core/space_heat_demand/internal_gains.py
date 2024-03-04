#!/usr/bin/env python3

"""
This module provides objects to represent the internal gains.
"""

# Local imports
import core.units as units


class InternalGains:
    """ An object to represent internal gains """

    def __init__(self, total_internal_gains, simulation_time, start_day, time_series_step):
        """ Construct a InternalGains object

        Arguments:
        total_internal_gains -- list of internal gains, in W/m2 (one entry per hour)
        simulation_time      -- reference to SimulationTime object
        start_day            -- first day of the time series, day of the year, 0 to 365 (single value)
        time_series_step     -- timestep of the time series data, in hours
        """
        self.__total_internal_gains = total_internal_gains
        self.__simulation_time  = simulation_time
        self.__start_day = start_day
        self.__time_series_step = time_series_step

    def total_internal_gain(self, zone_area):
        """ Return the total internal gain for the current timestep in W"""
        return self.__total_internal_gains[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)] * zone_area


class ApplianceGains:
    """ An object to represent internal gains and energy consumption from appliances"""

    def __init__(self, total_energy_supply, energy_supply_conn, gains_fraction, simulation_time, start_day, time_series_step):
        """ Construct a InternalGains object

        Arguments:
        total_energy_supply      -- list of energy supply from appliances, in W / m2 (one entry per hour)
        energy_supply_connection -- reference to EnergySupplyConnection object representing
                                    the electricity supply attached to the appliance
        gains_fraction           -- fraction of energy supply which is counted as an internal gain
        simulation_time          -- reference to SimulationTime object
        start_day                -- first day of the time series, day of the year, 0 to 365 (single value)
        time_series_step         -- timestep of the time series data, in hours
        """
        self.__total_energy_supply = total_energy_supply
        self.__energy_supply_conn = energy_supply_conn
        self.__gains_fraction = gains_fraction
        self.__simulation_time  = simulation_time
        self.__start_day = start_day
        self.__time_series_step = time_series_step

    def total_internal_gain(self, zone_area):
        """ Return the total internal gain for the current timestep, in W """
        # Forward elctricity demand (in kWh) to relevant EnergySupply object
        total_energy_supplied = self.__total_energy_supply[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)] 
        total_energy_supplied_W = total_energy_supplied * zone_area # convert to W
        total_energy_supplied_kWh = total_energy_supplied_W / units.W_per_kW * self.__simulation_time.timestep() # convert to kWh

        self.__energy_supply_conn.demand_energy(total_energy_supplied_kWh)

        return total_energy_supplied_W * self.__gains_fraction
