#!/usr/bin/env python3

"""
This module contains objects that represent electric battery systems.
"""

# Standard library imports

# Local imports

class ElectricBattery:
    """ An object to represent an electric battery system """

    def __init__(self, capacity, charge_discharge_efficiency):
        """ Construct an ElectricBattery object

        Arguments:
        capacity                    -- the maximum capacity of the battery (kWh)
        charge_discharge_efficiency -- charge/discharge round trip efficiency of battery
                                       system (between 0 & 1)

        Other variables:
        current_energy_stored -- the current energy stored in the battery at the
                                 end of hour (kWh)
        """
        self.__capacity = capacity
        self.__charge_discharge_efficiency = charge_discharge_efficiency
        self.__current_energy_stored = 0

    def charge_discharge_battery(self, elec_demand):
        """
        Arguments:
        elec_demand -- the supply (-ve) or demand (+ve) to/on the electric battery (kWh)

        Other variables:
        energy_available_to_charge_battery -- the total energy that would charge/discharge the battery
                                              including losses from charging efficiency (kWh)
        current_energy_stored_unconstrained -- Current energy stored in battery + the total energy that
                                               would charge/discharge the battery without minimum/maximum
                                               constraints of the battery (kWh)
        energy_accepted_by_battery -- The total energy the battery is able to supply or charge (kWh)
        """
        if elec_demand < 0: #Charging battery
            energy_available_to_charge_battery = (-elec_demand)*((self.__charge_discharge_efficiency) ** 0.5)
        else: #Discharging battery
            energy_available_to_charge_battery = (-elec_demand)/((self.__charge_discharge_efficiency) ** 0.5)
        #Charge/discharge the battery by the amount available
        current_energy_stored_unconstrained = self.__current_energy_stored + energy_available_to_charge_battery
        prev_energy_stored = self.__current_energy_stored
        #Energy stored cannot be > battery capacity or < 0
        self.__current_energy_stored = min(self.__capacity, max(0, current_energy_stored_unconstrained))
        energy_accepted_by_battery = self.__current_energy_stored - prev_energy_stored
        #Return the supply/demand energy the battery can accept (including charging/discharging losses)
        if elec_demand < 0: #Charging battery
            return -energy_accepted_by_battery/((self.__charge_discharge_efficiency) ** 0.5)
        else: #Discharging battery
            return -energy_accepted_by_battery*((self.__charge_discharge_efficiency) ** 0.5)
