#!/usr/bin/env python3

"""
This module contains the hot water demand calculations.
"""

# Standard library imports
import sys

# Local imports
from core.pipework import Pipework
import core.units as units
import core.water_heat_demand.misc as misc
from core.water_heat_demand.shower import MixerShower, InstantElecShower
from core.water_heat_demand.bath import Bath
from core.water_heat_demand.other_hot_water_uses import OtherHotWater


class DHWDemand:

    def __init__(
            self,
            showers_dict,
            baths_dict,
            other_hw_users_dict,
            hw_pipework_dict,
            cold_water_sources,
            wwhrs,
            energy_supplies,
            event_schedules,
            ):
        """ Construct a DHWDemand object """
        self.__event_schedules = event_schedules

        def dict_to_shower(name, data):
            """ Parse dictionary of shower data and return approprate shower object """
            cold_water_source = cold_water_sources[data['ColdWaterSource']]
            # TODO Need to handle error if ColdWaterSource name is invalid.

            shower_type = data['type']
            if shower_type == 'MixerShower':
                wwhrs_instance = None
                if 'WWHRS' in data:
                    wwhrs_instance = wwhrs[data['WWHRS']] # find the instance of WWHRS linked to by the shower

                shower = MixerShower(data['flowrate'], cold_water_source, wwhrs_instance)
            elif shower_type == 'InstantElecShower':
                energy_supply = energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                shower = InstantElecShower(
                    data['rated_power'],
                    cold_water_source,
                    energy_supply_conn,
                    )
            else:
                sys.exit(name + ': shower type (' + shower_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return shower

        self.__showers = {}
        no_of_showers = 0
        for name, data in showers_dict.items():
            self.__showers[name] = dict_to_shower(name, data)
            # Count number of showers that draw from HW system
            if data['type'] != 'InstantElecShower':
                no_of_showers += 1


        def dict_to_baths(name, data):
            """ Parse dictionary of bath data and return approprate bath object """
            cold_water_source = cold_water_sources[data['ColdWaterSource']]
            # TODO Need to handle error if ColdWaterSource name is invalid.

            bath = Bath(data['size'], cold_water_source, data['flowrate'])

            return bath

        self.__baths = {}
        for name, data in baths_dict.items():
            self.__baths[name] = dict_to_baths(name, data)

        def dict_to_other_water_events(name, data):
            """ Parse dictionary of bath data and return approprate other event object """
            cold_water_source = cold_water_sources[data['ColdWaterSource']]
            # TODO Need to handle error if ColdWaterSource name is invalid.

            other_event = OtherHotWater(data['flowrate'], cold_water_source)

            return other_event

        self.__other_hw_users = {}
        for name, data in other_hw_users_dict.items():
            self.__other_hw_users[name] = dict_to_other_water_events(name, data)

        total_no_of_hot_water_tapping_points = \
            no_of_showers + len(self.__baths.keys()) + len(self.__other_hw_users.keys())

        def dict_to_water_distribution_system(name, data):
            # go through internal then external distribution system

            # Calculate average length of pipework between HW system and tapping point
            length_average = data["length"] / total_no_of_hot_water_tapping_points

            pipework = Pipework(
                data["internal_diameter_mm"] / units.mm_per_m,
                data["external_diameter_mm"] / units.mm_per_m,
                length_average,
                data["insulation_thermal_conductivity"],
                data["insulation_thickness_mm"] / units.mm_per_m,
                data["surface_reflectivity"],
                data["pipe_contents"])
                
            return(pipework)

        self.__hw_distribution_pipework = {}
        for name, data in hw_pipework_dict.items():
            self.__hw_distribution_pipework[name] = dict_to_water_distribution_system(name, data)

    def hot_water_demand(self, t_idx):
        """ Calculate the hot water demand for the current timestep

        Arguments:
        t_idx -- timestep index/count
        """
        hw_demand_vol = 0.0
        hw_energy_demand = 0.0
        hw_duration = 0.0
        all_events = 0.0
        vol_hot_water_equiv_elec_shower = 0.0

        for name, shower in self.__showers.items():
            # Get all shower use events for the current timestep
            usage_events = self.__event_schedules['Shower'][name][t_idx]
            the_cold_water_temp = shower.get_cold_water_source()
            cold_water_temperature = the_cold_water_temp.temperature()

            # If shower is used in the current timestep, get details of use
            # and calculate HW demand from shower

            # TODO revisit structure and eliminate the branch on the type
            if usage_events is not None:
                for event in usage_events:
                    shower_temp = event['temperature']
                    shower_duration = event['duration']
                    hw_demand_i = shower.hot_water_demand(shower_temp, shower_duration)
                    if not isinstance(shower, InstantElecShower):
                        # don't add hw demand and pipework loss from electric shower
                        hw_demand_vol += hw_demand_i
                        hw_energy_demand += misc.water_demand_to_kWh(
                            hw_demand_i,
                            shower.get_temp_hot(),
                            cold_water_temperature
                            )
                        hw_duration += event['duration'] # shower minutes duration
                        all_events += 1
                    else:
                        # If electric shower, function returns equivalent
                        # amount of hot water for internal gains calculation
                        vol_hot_water_equiv_elec_shower += hw_demand_i

        for name, other in self.__other_hw_users.items():
            # Get all other use events for the current timestep
            usage_events = self.__event_schedules['Other'][name][t_idx]
            the_cold_water_temp = other.get_cold_water_source()
            cold_water_temperature = the_cold_water_temp.temperature()
            
            # If other is used in the current timestep, get details of use
            # and calculate HW demand from other
            if usage_events is not None:
                for event in usage_events:
                    other_temp = event['temperature']
                    other_duration = event['duration']
                    hw_demand_vol += other.hot_water_demand(other_temp, other_duration)
                    hw_energy_demand += misc.water_demand_to_kWh(
                        other.hot_water_demand(other_temp, other_duration),
                        other.get_temp_hot(),
                        cold_water_temperature
                        )
                    hw_duration += event['duration'] # other minutes duration
                    all_events += 1
                    

        for name, bath in self.__baths.items():
            # Get all bath use events for the current timestep
            usage_events = self.__event_schedules['Bath'][name][t_idx]
            the_cold_water_temp = bath.get_cold_water_source()
            cold_water_temperature = the_cold_water_temp.temperature()

            # Assume flow rate for bath event is the same as other hot water events
            peak_flowrate = bath.get_flowrate()

            # If bath is used in the current timestep, get details of use
            # and calculate HW demand from bath
            # Note that bath size is the total water used per bath, not the total capacity of the bath
            if usage_events is not None:
                for event in usage_events:
                    bath_temp = event['temperature']
                    hw_demand_vol += bath.hot_water_demand(bath_temp)
                    # litres bath  / litres per minute flowrate = minutes
                    bath_duration = bath.get_size() / peak_flowrate
                    hw_energy_demand += misc.water_demand_to_kWh(
                        bath.hot_water_demand(bath_temp),
                        bath.get_temp_hot(),
                        cold_water_temperature
                        )
                    hw_duration += bath_duration
                    all_events += 1

        hw_vol_at_tapping_points = hw_demand_vol + vol_hot_water_equiv_elec_shower

        if self.__hw_distribution_pipework:
            vol_hot_water_left_in_pipework \
                = self.__hw_distribution_pipework['internal'].volume_litres() \
                + self.__hw_distribution_pipework['external'].volume_litres()
            hw_demand_vol += all_events * vol_hot_water_left_in_pipework

        # Return:
        # - litres hot water per timestep (demand on hw system)
        # - litres hot water per timestep (output at tapping points)
        # - minutes demand per timestep,
        # - number of events in timestep
        # - hot water energy demand (kWh)
        return \
            hw_demand_vol, \
            hw_vol_at_tapping_points, \
            hw_duration, \
            all_events, \
            hw_energy_demand

    def calc_pipework_losses(
            self,
            delta_t_h,
            hw_duration,
            no_of_hw_events,
            demand_water_temperature,
            internal_air_temperature,
            external_air_temperature,
            ):

        if not self.__hw_distribution_pipework:
            # Return heat loss in kWh for the timestep
            return 0.0, 0.0

        hot_water_time_fraction = hw_duration / (delta_t_h * units.minutes_per_hour)
        if hot_water_time_fraction > 1:
            hot_water_time_fraction = 1

        '''
        TODO For now, ignore heat loss from pipes while water is flowing, as
             this is is not currently added to hot water demand, but is added
             to the internal gains. This would mean that reducing insulation
             would reduce overall energy demand, which would not be correct.
        pipework_watts_heat_loss_internal = self.__hw_distribution_pipework["internal"].heat_loss(
            demand_water_temperature,
            internal_air_temperature,
            )
        pipework_watts_heat_loss_external = self.__hw_distribution_pipework["external"].heat_loss(
            demand_water_temperature,
            external_air_temperature,
            )

        # only calculate loss for times when there is hot water in the pipes - multiply by time fraction to get to kWh
        pipework_heat_loss_internal \
            = pipework_watts_heat_loss_internal \
            * hot_water_time_fraction \
            * delta_t_h \
            / units.W_per_kW # convert to kWh
        pipework_heat_loss_external \
            = pipework_watts_heat_loss_external \
            * hot_water_time_fraction \
            * delta_t_h \
            / units.W_per_kW # convert to kWh
        '''
        pipework_heat_loss_internal = 0.0
        pipework_heat_loss_external = 0.0

        pipework_heat_loss_internal \
            += no_of_hw_events \
             * self.__hw_distribution_pipework["internal"].cool_down_loss(
                demand_water_temperature,
                internal_air_temperature
                )
        pipework_heat_loss_external \
            += no_of_hw_events \
             * self.__hw_distribution_pipework["external"].cool_down_loss(
                demand_water_temperature,
                external_air_temperature,
                )

        # Return heat loss in kWh for the timestep
        return pipework_heat_loss_internal, pipework_heat_loss_external
