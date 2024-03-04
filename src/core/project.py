#!/usr/bin/env python3

"""
This module provides the high-level control flow for the core calculation, and
initialises the relevant objects in the core model.
"""

# Standard library imports
import sys
from math import ceil

# Local imports
import core.units as units
from core.simulation_time import SimulationTime
from core.external_conditions import ExternalConditions
from core.schedule import expand_schedule, expand_events
from core.controls.time_control import \
    OnOffTimeControl, SetpointTimeControl, ToUChargeControl, \
    OnOffCostMinimisingTimeControl
from core.cooling_systems.air_conditioning import AirConditioning
from core.energy_supply.energy_supply import EnergySupply
from core.energy_supply.elec_battery import ElectricBattery
from core.energy_supply.pv import PhotovoltaicSystem
from core.heating_systems.emitters import Emitters
from core.heating_systems.heat_pump import HeatPump, HeatPump_HWOnly, SourceType
from core.heating_systems.storage_tank import \
    ImmersionHeater, SolarThermalSystem, StorageTank, PVDiverter
from core.heating_systems.instant_elec_heater import InstantElecHeater
from core.heating_systems.elec_storage_heater import ElecStorageHeater
from core.heating_systems.boiler import Boiler, BoilerServiceWaterCombi
from core.heating_systems.heat_battery import HeatBattery
from core.heating_systems.heat_network import HeatNetwork
from core.space_heat_demand.zone import Zone
from core.space_heat_demand.building_element import \
    BuildingElementOpaque, BuildingElementTransparent, BuildingElementGround, \
    BuildingElementAdjacentZTC, BuildingElementAdjacentZTU_Simple, \
    BuildingElement
from core.space_heat_demand.ventilation_element import \
    VentilationElementInfiltration, WholeHouseExtractVentilation, \
    MechnicalVentilationHeatRecovery, NaturalVentilation,\
    air_change_rate_to_flow_rate, WindowOpeningForCooling
from core.space_heat_demand.thermal_bridge import \
    ThermalBridgeLinear, ThermalBridgePoint
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.water_heat_demand.dhw_demand import DHWDemand
from core.space_heat_demand.internal_gains import InternalGains, ApplianceGains
import core.water_heat_demand.misc as misc
from core.ductwork import Ductwork
import core.heating_systems.wwhrs as wwhrs
from core.heating_systems.point_of_use import PointOfUse
from core.units import Kelvin2Celcius


class Project:
    """ An object to represent the overall model to be simulated """

    def __init__(
            self,
            proj_dict,
            print_heat_balance,
            detailed_output_heating_cooling,
            use_fast_solver,
            ):
        """ Construct a Project object and the various components of the simulation

        Arguments:
        proj_dict -- dictionary of project data, containing nested dictionaries
                     and lists of input data for system components, external
                     conditions, occupancy etc.
        print_heat_balance -- flag to idindicate whether to print the heat balance outputs
        detailed_output_heating_cooling -- flag to indicate whether detailed output should be
                                           provided for heating and cooling (where possible)
        use_fast_solver -- flag to indicate whether to use the optimised solver (results
                           may differ slightly due to reordering of floating-point ops)

        Other (self.__) variables:
        simtime            -- SimulationTime object for this Project
        external_conditions -- ExternalConditions object for this Project
        cold_water_sources -- dictionary of ColdWaterSource objects with names as keys
        energy_supplies    -- dictionary of EnergySupply objects with names as keys
        controls           -- dictionary of control objects (of varying types) with names as keys
        hot_water_sources  -- dictionary of hot water source objects (of varying types)
                              with names as keys
        showers            -- dictionary of shower objects (of varying types) with names as keys
        space_heat_systems -- dictionary of space heating system objects (of varying
                              types) with names as keys
        zones              -- dictionary of Zone objects with names as keys
        """
        self.__detailed_output_heating_cooling = detailed_output_heating_cooling

        self.__simtime = SimulationTime(
            proj_dict['SimulationTime']['start'],
            proj_dict['SimulationTime']['end'],
            proj_dict['SimulationTime']['step'],
            )

        # TODO Some inputs are not currently used, so set to None here rather
        #      than requiring them in input file.
        # TODO Read timezone from input file. For now, set timezone to 0 (GMT)
        # Let direct beam conversion input be optional, this will be set if comes from weather file.
        if proj_dict['ExternalConditions']['direct_beam_conversion_needed']:
            dir_beam_conversion = proj_dict['ExternalConditions']['direct_beam_conversion_needed']
        else:
            dir_beam_conversion = False

        self.__external_conditions = ExternalConditions(
            self.__simtime,
            proj_dict['ExternalConditions']['air_temperatures'],
            proj_dict['ExternalConditions']['wind_speeds'],
            proj_dict['ExternalConditions']['diffuse_horizontal_radiation'],
            proj_dict['ExternalConditions']['direct_beam_radiation'],
            proj_dict['ExternalConditions']['solar_reflectivity_of_ground'],
            proj_dict['ExternalConditions']['latitude'],
            proj_dict['ExternalConditions']['longitude'],
            0, #proj_dict['ExternalConditions']['timezone'],
            0, #proj_dict['ExternalConditions']['start_day'],
            365, #proj_dict['ExternalConditions']['end_day'],
            1, #proj_dict['ExternalConditions']['time_series_step'],
            None, #proj_dict['ExternalConditions']['january_first'],
            None, #proj_dict['ExternalConditions']['daylight_savings'],
            None, #proj_dict['ExternalConditions']['leap_day_included'],
            dir_beam_conversion,
            proj_dict['ExternalConditions']['shading_segments'],
            )

        if 'flat' in proj_dict['Infiltration']['build_type']:
            storey_of_dwelling = proj_dict['Infiltration']['storey_of_dwelling']
        else:
            storey_of_dwelling = None

        self.__infiltration = VentilationElementInfiltration(
            proj_dict['Infiltration']['storeys_in_building'],
            proj_dict['Infiltration']['shelter'],
            proj_dict['Infiltration']['build_type'],
            proj_dict['Infiltration']['test_result'],
            proj_dict['Infiltration']['test_type'],
            proj_dict['Infiltration']['env_area'],
            proj_dict['Infiltration']['volume'],
            proj_dict['Infiltration']['sheltered_sides'],
            proj_dict['Infiltration']['open_chimneys'],
            proj_dict['Infiltration']['open_flues'],
            proj_dict['Infiltration']['closed_fire'],
            proj_dict['Infiltration']['flues_d'],
            proj_dict['Infiltration']['flues_e'],
            proj_dict['Infiltration']['blocked_chimneys'],
            proj_dict['Infiltration']['extract_fans'],
            proj_dict['Infiltration']['passive_vents'],
            proj_dict['Infiltration']['gas_fires'],
            self.__external_conditions,
            storey_of_dwelling,
            )

        self.__cold_water_sources = {}
        for name, data in proj_dict['ColdWaterSource'].items():
            self.__cold_water_sources[name] \
                = ColdWaterSource(data['temperatures'], self.__simtime, data['start_day'], data['time_series_step'])

        self.__energy_supplies = {}
        energy_supply_unmet_demand = EnergySupply('unmet_demand', self.__simtime)
        self.__energy_supplies['_unmet_demand'] = energy_supply_unmet_demand
        diverters = {}
        for name, data in proj_dict['EnergySupply'].items():
            if 'ElectricBattery' in data:
                self.__energy_supplies[name] = EnergySupply(
                    data['fuel'],
                    self.__simtime,
                    ElectricBattery(
                        data['ElectricBattery']['capacity'],
                        data['ElectricBattery']['charge_discharge_efficiency'],
                        )
                    )
            else:
                self.__energy_supplies[name] = EnergySupply(data['fuel'], self.__simtime)
            # TODO Consider replacing fuel type string with fuel type object

            if 'diverter' in data:
                diverters[name] = data['diverter']

        self.__internal_gains = {}
        if 'InternalGains' in proj_dict:
            for name, data in proj_dict['InternalGains'].items():
                self.__internal_gains[name] = InternalGains(
                                                 expand_schedule(
                                                     float,
                                                     data['schedule'],
                                                     "main",
                                                     False,
                                                     ),
                                                 self.__simtime,
                                                 data['start_day'],
                                                 data['time_series_step']
                                                 )

        def dict_to_ctrl(name, data):
            """ Parse dictionary of control data and return appropriate control object """
            ctrl_type = data['type']
            if ctrl_type == 'OnOffTimeControl':
                sched = expand_schedule(bool, data['schedule'], "main", False)
                ctrl = OnOffTimeControl(
                    schedule=sched,
                    simulation_time=self.__simtime,
                    start_day=data['start_day'],
                    time_series_step=data['time_series_step']
                )
            elif ctrl_type == 'SetpointTimeControl':
                sched = expand_schedule(float, data['schedule'], "main", True)

                setpoint_min = None
                setpoint_max = None
                default_to_max = None
                advanced_start = 0.0
                if 'setpoint_min' in data:
                    setpoint_min = data['setpoint_min']
                if 'setpoint_max' in data:
                    setpoint_max = data['setpoint_max']
                if 'default_to_max' in data:
                    default_to_max = data['default_to_max']
                if 'advanced_start' in data:
                    advanced_start = data['advanced_start']

                ctrl = SetpointTimeControl(
                    schedule=sched,
                    simulation_time=self.__simtime,
                    start_day=data['start_day'],
                    time_series_step=data['time_series_step'],
                    setpoint_min=setpoint_min,
                    setpoint_max=setpoint_max,
                    default_to_max=default_to_max,
                    duration_advanced_start=advanced_start,
                )
            elif ctrl_type == 'ToUChargeControl':
                sched = expand_schedule(bool, data['schedule'], "main", False)

                # Simulating manual charge control
                # Set charge_level to 1.0 (max) for each day of simulation (plus 1)
                charge_level = [1.0] * ceil((self.__simtime.total_steps() * self.__simtime.timestep())/24 + 1)
                # If charge_level is present in the input file overwrite initial vector
                # User can specify a vector with all days (plus 1), or as a single float value to be used for each day
                if 'charge_level' in data:
                    # If the input is a vector, use the vector
                    if isinstance(data['charge_level'], (list, tuple)):
                        charge_level=data['charge_level']
                    # Else, if input is a single value, use that value for each day of simulation
                    else:
                        charge_level = [data['charge_level']] * ceil((self.__simtime.total_steps() * self.__simtime.timestep())/24 + 1)

                ctrl = ToUChargeControl(
                    schedule=sched,
                    simulation_time=self.__simtime,
                    start_day=data['start_day'],
                    time_series_step=data['time_series_step'],
                    charge_level=charge_level
                )
            elif ctrl_type == 'OnOffCostMinimisingTimeControl':
                sched = expand_schedule(float, data['schedule'], "main", False)
                ctrl = OnOffCostMinimisingTimeControl(
                    sched,
                    self.__simtime,
                    data['start_day'],
                    data['time_series_step'],
                    data['time_on_daily'],
                    )
            else:
                sys.exit(name + ': control type (' + ctrl_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return ctrl

        self.__controls = {}
        for name, data in proj_dict['Control'].items():
            self.__controls[name] = dict_to_ctrl(name, data)

        def dict_to_wwhrs(name, data):
            """ Parse dictionary of WWHRS source data and return approprate WWHRS source object """
            wwhrs_source_type = data['type']
            if wwhrs_source_type == 'WWHRS_InstantaneousSystemB':
                cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
                # TODO Need to handle error if ColdWaterSource name is invalid.

                the_wwhrs = wwhrs.WWHRS_InstantaneousSystemB(
                    data['flow_rates'],
                    data['efficiencies'],
                    cold_water_source,
                    data['utilisation_factor']
                    )
            else:
                if wwhrs_source_type == 'WWHRS_InstantaneousSystemC':
                    cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
                    # TODO Need to handle error if ColdWaterSource name is invalid.
    
                    the_wwhrs = wwhrs.WWHRS_InstantaneousSystemC(
                        data['flow_rates'],
                        data['efficiencies'],
                        cold_water_source,
                        data['utilisation_factor']
                        )
                else:
                    if wwhrs_source_type == 'WWHRS_InstantaneousSystemA':
                        cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
                        # TODO Need to handle error if ColdWaterSource name is invalid.
        
                        the_wwhrs = wwhrs.WWHRS_InstantaneousSystemA(
                            data['flow_rates'],
                            data['efficiencies'],
                            cold_water_source,
                            data['utilisation_factor']
                            )
                    else:
                        sys.exit(name + ': WWHRS (' + wwhrs_source_type + ') not recognised.')
                        # TODO Exit just the current case instead of whole program entirely?
            return the_wwhrs
            
        if 'WWHRS' in proj_dict:
            self.__wwhrs = {}
            for name, data in proj_dict['WWHRS'].items():
                self.__wwhrs[name] = dict_to_wwhrs(name, data)
        else:
            self.__wwhrs = None

        def dict_to_event_schedules(data):
            """ Process list of events (for hot water draw-offs, appliance use etc.) """
            sim_timestep = self.__simtime.timestep()
            tot_timesteps = self.__simtime.total_steps()
            return expand_events(data, sim_timestep, tot_timesteps)

        self.__event_schedules = {}
        for sched_type, schedules in proj_dict['Events'].items():
            if sched_type not in self.__event_schedules:
                self.__event_schedules[sched_type] = {}
            for name, data in schedules.items():
                self.__event_schedules[sched_type][name] = dict_to_event_schedules(data)

        # TODO - this assumes there is only one hot water source, and if any
        # hot water source is point of use, they all are. In future, allow more
        # than one hot water source and assign hot water source to each outlet?
        if proj_dict['HotWaterSource']['hw cylinder']['type'] == 'PointOfUse':
            hw_pipework_dict = {}
        else:
            hw_pipework_dict = proj_dict['Distribution']

        self.__dhw_demand = DHWDemand(
            proj_dict['Shower'],
            proj_dict['Bath'],
            proj_dict['Other'],
            hw_pipework_dict,
            self.__cold_water_sources,
            self.__wwhrs,
            self.__energy_supplies,
            self.__event_schedules,
            )
 
        def dict_to_building_element(name, data):
            building_element_type = data['type']

            # Calculate r_c from u_value if only the latter has been provided
            data['r_c'] = self.__init_resistance_or_uvalue(name, data)

            if building_element_type == 'BuildingElementOpaque':
                building_element = BuildingElementOpaque(
                    data['area'],
                    data['pitch'],
                    data['a_sol'],
                    data['r_c'],
                    data['k_m'],
                    data['mass_distribution_class'],
                    self.__init_orientation(data['orientation360']),
                    data['base_height'],
                    data['height'],
                    data['width'],
                    self.__external_conditions,
                    )
            elif building_element_type == 'BuildingElementTransparent':
                building_element = BuildingElementTransparent(
                    data['pitch'],
                    data['r_c'],
                    self.__init_orientation(data['orientation360']),
                    data['g_value'],
                    data['frame_area_fraction'],
                    data['base_height'],
                    data['height'],
                    data['width'],
                    data['shading'],
                    self.__external_conditions,
                    )
            elif building_element_type == 'BuildingElementGround':
                building_element = BuildingElementGround(
                    data['area'],
                    data['pitch'],
                    data['u_value'],
                    data['r_f'],
                    data['k_m'],
                    data['mass_distribution_class'],
                    data['h_pi'],
                    data['h_pe'],
                    data['perimeter'],
                    data['psi_wall_floor_junc'],
                    self.__external_conditions,
                    self.__simtime,
                    )
            elif building_element_type == 'BuildingElementAdjacentZTC':
                building_element = BuildingElementAdjacentZTC(
                    data['area'],
                    data['pitch'],
                    data['r_c'],
                    data['k_m'],
                    data['mass_distribution_class'],
                    self.__external_conditions,
                    )
            elif building_element_type == 'BuildingElementAdjacentZTU_Simple':
                building_element = BuildingElementAdjacentZTU_Simple(
                    data['area'],
                    data['pitch'],
                    data['r_c'],
                    data['r_u'],
                    data['k_m'],
                    data['mass_distribution_class'],
                    self.__external_conditions,
                    )
            else:
                sys.exit( name + ': building element type ('
                        + building_element_type + ') not recognised.' )
                # TODO Exit just the current case instead of whole program entirely?
            return building_element

        def dict_to_ventilation_element(name, data):
            ventilation_element_type = data['type']
            ductwork = None
            if ventilation_element_type == 'WHEV': # Whole house extract ventilation
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                ventilation_element = WholeHouseExtractVentilation(
                    data['req_ach'],
                    data['SFP'],
                    self.__infiltration.infiltration(),
                    energy_supply_conn,
                    self.__external_conditions,
                    self.__simtime,
                    )
            elif ventilation_element_type == 'MVHR':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                ventilation_element = MechnicalVentilationHeatRecovery(
                    data['req_ach'],
                    data['SFP'],
                    data['efficiency'],
                    energy_supply_conn,
                    self.__external_conditions,
                    self.__simtime,
                    )
                    
                ductwork = Ductwork(
                    data['ductwork']['internal_diameter_mm'] / units.mm_per_m,
                    data['ductwork']['external_diameter_mm'] / units.mm_per_m,
                    data['ductwork']['length_in'],
                    data['ductwork']['length_out'],
                    data['ductwork']['insulation_thermal_conductivity'],
                    data['ductwork']['insulation_thickness_mm'] / units.mm_per_m,
                    data['ductwork']['reflective'],
                    data['ductwork']['MVHR_location']
                    )
            elif ventilation_element_type == 'NatVent':
                ventilation_element = NaturalVentilation(
                    data['req_ach'],
                    self.__infiltration.infiltration(),
                    self.__external_conditions,
                    )
            else:
                sys.exit( name + ': ventilation element type ('
                      + ventilation_element_type + ') not recognised.' )
                # TODO Exit just the current case instead of whole program entirely?
            return ventilation_element, ductwork


        if 'Ventilation' in proj_dict:
            self.__ventilation, self.__space_heating_ductwork = \
                dict_to_ventilation_element('Ventilation system', proj_dict['Ventilation'])
            air_change_rate_req = proj_dict['Ventilation']['req_ach']
        else:
            self.__ventilation, self.__space_heating_ductwork = None, None

        def dict_to_thermal_bridging(data):
            # If data is for individual thermal bridges, initialise the relevant
            # objects and return a list of them. Otherwise, just use the overall
            # figure given.
            if isinstance(data, dict):
                thermal_bridging = []
                for tb_name, tb_data in data.items():
                    tb_type = tb_data['type']
                    if tb_type == 'ThermalBridgeLinear':
                        tb = ThermalBridgeLinear(
                                tb_data['linear_thermal_transmittance'],
                                tb_data['length']
                                )
                    elif tb_type == 'ThermalBridgePoint':
                        tb = ThermalBridgePoint(tb_data['heat_transfer_coeff'])
                    else:
                        sys.exit( tb_name + ': thermal bridge type ('
                                + tb_type + ') not recognised.' )
                        # TODO Exit just the current case instead of whole program entirely?
                    thermal_bridging.append(tb)
            else:
                thermal_bridging = data
            return thermal_bridging

        self.__heat_system_name_for_zone = {}
        self.__cool_system_name_for_zone = {}
        opening_area_total = 0.0
        for z_data in proj_dict['Zone'].values():
            for building_element_data in z_data['BuildingElement'].values():
                if building_element_data['type'] == 'BuildingElementTransparent':
                    opening_area_total \
                        += building_element_data['height'] * building_element_data['width']

        def dict_to_zone(name, data):
            # Record which heating and cooling system this zone is heated/cooled by (if applicable)
            if 'SpaceHeatSystem' in data:
                # Check that no heating system has been assigned to more than one zone
                if data['SpaceHeatSystem'] in self.__heat_system_name_for_zone.values():
                    sys.exit('Invalid input: SpaceHeatSystem (' + data['SpaceHeatSystem'] 
                           + ') has been assigned to more than one Zone')
                self.__heat_system_name_for_zone[name] = data['SpaceHeatSystem']
            else:
                self.__heat_system_name_for_zone[name] = None
            if 'SpaceCoolSystem' in data:
                # Check that no cooling system has been assigned to more than one zone
                if data['SpaceCoolSystem'] in self.__cool_system_name_for_zone.values():
                    sys.exit('Invalid input: SpaceCoolSystem (' + data['SpaceCoolSystem'] 
                           + ') has been assigned to more than one Zone')
                self.__cool_system_name_for_zone[name] = data['SpaceCoolSystem']
            else:
                self.__cool_system_name_for_zone[name] = None

            # Read in building elements and add to list
            building_elements = []
            for building_element_name, building_element_data in data['BuildingElement'].items():
                building_elements.append(
                    dict_to_building_element(building_element_name, building_element_data)
                    )

            if 'Window_Opening_For_Cooling' in proj_dict:
                openings = list(filter(
                    lambda be: isinstance(be, BuildingElementTransparent),
                    building_elements,
                    ))
                opening_area_zone = sum(op.area for op in openings)
                opening_area_equivalent \
                    = proj_dict['Window_Opening_For_Cooling']['equivalent_area'] \
                    * opening_area_zone / opening_area_total
                control = self.__controls[proj_dict['Zone'][name]['Control_WindowOpening']]
                if isinstance(self.__ventilation, NaturalVentilation):
                    natvent = self.__ventilation
                else:
                    natvent = None
                vent_cool_extra = WindowOpeningForCooling(
                    opening_area_equivalent,
                    self.__external_conditions,
                    openings,
                    control,
                    natvent = natvent,
                    )
            else:
                vent_cool_extra = None

            # Read in thermal bridging data
            thermal_bridging = dict_to_thermal_bridging(data['ThermalBridging'])

            # Read in ventilation elements and add to list
            # All zones have infiltration, so start list with infiltration object
            vent_elements = [self.__infiltration]
            # Add any additional ventilation elements
            if self.__ventilation is not None:
                vent_elements.append(self.__ventilation)

            return Zone(
                data['area'],
                data['volume'],
                building_elements,
                thermal_bridging,
                vent_elements,
                self.__external_conditions.air_temp(),
                data['temp_setpnt_init'],
                vent_cool_extra = vent_cool_extra,
                print_heat_balance = print_heat_balance,
                use_fast_solver = use_fast_solver,
                )

        self.__zones = {}
        self.__energy_supply_conn_unmet_demand_zone = {}
        for name, data in proj_dict['Zone'].items():
            self.__zones[name] = dict_to_zone(name, data)
            self.__energy_supply_conn_unmet_demand_zone[name] \
                = self.__energy_supplies['_unmet_demand'].connection(name)

        self.__total_floor_area = sum(zone.area() for zone in self.__zones.values())
        self.__total_volume = sum(zone.volume() for zone in self.__zones.values())

        # Add internal gains from applicances to the internal gains dictionary and
        # create an energy supply connection for appliances
        for name, data in proj_dict['ApplianceGains'].items():
            energy_supply = self.__energy_supplies[data['EnergySupply']]
            # TODO Need to handle error if EnergySupply name is invalid.
            energy_supply_conn = energy_supply.connection(name)
            
            # Convert energy supplied to appliances from W to W / m2
            total_energy_supply = []
            for energy_data in expand_schedule(float, data['schedule'], "main", False):
                total_energy_supply.append(energy_data / self.__total_floor_area)

            self.__internal_gains[name] = ApplianceGains(
                                             total_energy_supply,
                                             energy_supply_conn,
                                             data['gains_fraction'],
                                             self.__simtime,
                                             data['start_day'],
                                             data['time_series_step']
                                             )

        # Where wet distribution heat source provide more than one service, some
        # calculations can only be performed after all services have been
        # calculated. Give these systems a timestep_end function and add these
        # systems to the following list, which will be iterated over later.
        self.__timestep_end_calcs = []

        def dict_to_heat_source_wet(name, data):
            heat_source_type = data['type']
            if heat_source_type == 'HeatPump':
                if SourceType.is_exhaust_air(data['source_type']):
                    # Check that ventilation system is compatible with exhaust air HP
                    if type(self.__ventilation) \
                    not in (MechnicalVentilationHeatRecovery, WholeHouseExtractVentilation):
                        sys.exit('Exhaust air heat pump requires ventilation to be MVHR or WHEV.')
                    throughput_exhaust_air \
                        = air_change_rate_to_flow_rate(air_change_rate_req, self.__total_volume) \
                        * units.litres_per_cubic_metre
                else:
                    throughput_exhaust_air = None

                if SourceType.from_string(data['source_type']) == SourceType.HEAT_NETWORK:
                    energy_supply_HN = self.__energy_supplies[data['EnergySupply_heat_network']]
                    # TODO Check that EnergySupply object representing heat source
                    #      has an appropriate fuel type
                else:
                    energy_supply_HN = None

                energy_supply = self.__energy_supplies[data['EnergySupply']]
                energy_supply_conn_name_auxiliary = 'HeatPump_auxiliary: ' + name
                heat_source = HeatPump(
                    data,
                    energy_supply,
                    energy_supply_conn_name_auxiliary,
                    self.__simtime,
                    self.__external_conditions,
                    throughput_exhaust_air,
                    energy_supply_HN,
                    self.__detailed_output_heating_cooling
                    )
                self.__timestep_end_calcs.append(heat_source)
            elif heat_source_type == 'Boiler':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                energy_supply_aux = self.__energy_supplies[data['EnergySupply_aux']]
                energy_supply_conn_aux = energy_supply_aux.connection('Boiler_auxiliary: ' + name)
                heat_source = Boiler(
                    data,
                    energy_supply,
                    energy_supply_conn_aux,
                    self.__simtime,
                    self.__external_conditions,
                    )
                self.__timestep_end_calcs.append(heat_source)
            elif heat_source_type == 'HIU':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                energy_supply_conn_name_auxiliary = 'HeatNetwork_auxiliary: ' + name
                energy_supply_conn_name_building_level_distribution_losses \
                    = 'HeatNetwork_building_level_distribution_losses: ' + name
                heat_source = HeatNetwork(
                    data['power_max'],
                    data['HIU_daily_loss'],
                    data['building_level_distribution_losses'],
                    energy_supply,
                    energy_supply_conn_name_auxiliary,
                    energy_supply_conn_name_building_level_distribution_losses,
                    self.__simtime,
                    )
                self.__timestep_end_calcs.append(heat_source)
                # Create list of internal gains for each hour of the year, in W / m2
                internal_gains_HIU = [heat_source.HIU_loss() \
                                        * units.W_per_kW \
                                        / self.__total_floor_area]
                total_internal_gains_HIU = internal_gains_HIU * units.days_per_year * units.hours_per_day
                # Append internal gains object to self.__internal_gains dictionary
                if name in self.__internal_gains.keys():
                    sys.exit('Name of HIU duplicates name of an existing InternalGains object')
                self.__internal_gains[name] = InternalGains(
                    total_internal_gains_HIU,
                    self.__simtime,
                    0, # Start day of internal gains time series
                    1.0, # Timestep of internal gains time series
                    )
            elif heat_source_type == 'HeatBattery':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)
                charge_control: ToUChargeControl = self.__controls[data['ControlCharge']]
                heat_source = HeatBattery(
                    data,
                    charge_control,
                    energy_supply,
                    energy_supply_conn,
                    self.__simtime,
                    self.__external_conditions,
                    )
                self.__timestep_end_calcs.append(heat_source)
            else:
                sys.exit(name + ': heat source type (' \
                       + heat_source_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return heat_source

        # If one or more wet distribution heat sources have been provided, add them to the project
        self.__heat_sources_wet = {}
        # If no wet distribution heat sources have been provided, then skip.
        if 'HeatSourceWet' in proj_dict:
            for name, data in proj_dict['HeatSourceWet'].items():
                self.__heat_sources_wet[name] = dict_to_heat_source_wet(name, data)

        def dict_to_heat_source(name, data, temp_setpoint):
            """ Parse dictionary of heat source data and return approprate heat source object """
            if 'Control' in data.keys():
                ctrl = self.__controls[data['Control']]
                # TODO Need to handle error if Control name is invalid.
            else:
                ctrl = None

            heat_source_type = data['type']
            if heat_source_type == 'ImmersionHeater':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn_name = name
                energy_supply_conn = energy_supply.connection(name)

                heat_source = ImmersionHeater(
                    data['power'],
                    energy_supply_conn,
                    self.__simtime,
                    ctrl,
                    )
            elif heat_source_type == 'SolarThermalSystem':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn_name = name
                energy_supply_conn = energy_supply.connection(name)

                heat_source = SolarThermalSystem(
                    data['sol_loc'],
                    data['area_module'],
                    data['modules'],
                    data['peak_collector_efficiency'],
                    data['incidence_angle_modifier'],
                    data['first_order_hlc'],
                    data['second_order_hlc'],
                    data['collector_mass_flow_rate'],
                    data['power_pump'],
                    data['power_pump_control'],
                    energy_supply_conn,
                    data['tilt'],
                    self.__init_orientation(data['orientation360']),
                    data['solar_loop_piping_hlc'],
                    self.__external_conditions,
                    self.__simtime,
                    )
                
            elif heat_source_type == 'HeatSourceWet':
                cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
                energy_supply_conn_name = data['name'] + '_water_heating'

                heat_source_wet = self.__heat_sources_wet[data['name']]
                if isinstance(heat_source_wet, HeatPump):
                    heat_source = heat_source_wet.create_service_hot_water(
                        energy_supply_conn_name,
                        temp_setpoint,
                        55, # TODO Remove hard-coding of return temp
                        data['temp_flow_limit_upper'],
                        cold_water_source,
                        ctrl,
                        )
                elif isinstance(heat_source_wet, Boiler):
                    heat_source = heat_source_wet.create_service_hot_water_regular(
                        data,
                        energy_supply_conn_name,
                        temp_setpoint,
                        cold_water_source,
                        55, # TODO Remove hard-coding of return temp
                        ctrl,
                        )
                elif isinstance(heat_source_wet, HeatNetwork):
                    # Add heat network hot water service for feeding hot water cylinder
                    heat_source = heat_source_wet.create_service_hot_water_storage(
                        energy_supply_conn_name,
                        temp_setpoint,
                        ctrl,
                        )
                elif isinstance(heat_source_wet, HeatBattery):
                    heat_source = heat_source_wet.create_service_hot_water_regular(
                        data,
                        energy_supply_conn_name,
                        temp_setpoint,
                        cold_water_source,
                        55, # TODO Remove hard-coding of return temp
                        ctrl,
                        )
                else:
                    sys.exit(name + ': HeatSource type not recognised')
                    # TODO Exit just the current case instead of whole program entirely?
            elif heat_source_type == 'HeatPump_HWOnly':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn_name = name
                energy_supply_conn = energy_supply.connection(name)

                heat_source = HeatPump_HWOnly(
                    data['power_max'],
                    data['test_data'],
                    data['vol_hw_daily_average'],
                    energy_supply_conn,
                    self.__simtime,
                    ctrl,
                    )
            else:
                sys.exit(name + ': heat source type (' + heat_source_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return heat_source, energy_supply_conn_name

        # List of diverter objects (for end-of-timestep calculations
        self.__diverters = []

        def dict_to_hot_water_source(name, data):
            """ Parse dictionary of HW source data and return approprate HW source object """
            energy_supply_conn_names = []

            hw_source_type = data['type']
            if hw_source_type == 'StorageTank':
                cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
                # TODO Need to handle error if ColdWaterSource name is invalid.
                # TODO assuming here there is only one WWHRS
                if self.__wwhrs is not None:
                    for wwhrs_name in self.__wwhrs:
                        if isinstance(self.__wwhrs[wwhrs_name], wwhrs.WWHRS_InstantaneousSystemC) \
                        or isinstance(self.__wwhrs[wwhrs_name], wwhrs.WWHRS_InstantaneousSystemA):
                            cold_water_source = self.__wwhrs[wwhrs_name]

                if 'primary_pipework' in data:
                    primary_pipework = data['primary_pipework']
                    primary_pipework['internal_diameter'] \
                        = primary_pipework['internal_diameter_mm'] / units.mm_per_m
                    primary_pipework['external_diameter'] \
                        = primary_pipework['external_diameter_mm'] / units.mm_per_m
                    primary_pipework['insulation_thickness'] \
                        = primary_pipework['insulation_thickness_mm'] / units.mm_per_m
                else:
                    primary_pipework = None

                heat_source_dict= {}
                for heat_source_name, heat_source_data in data['HeatSource'].items():
                    heat_source, conn_name = dict_to_heat_source(
                        heat_source_name,
                        heat_source_data,
                        data['setpoint_temp'],
                        )
                    heat_source_dict[heat_source] = heat_source_data['heater_position'], \
                                                    heat_source_data['thermostat_position']
                    energy_supply_conn_names.append(conn_name)

                if 'Control_hold_at_setpnt' in data:
                    ctrl_hold_at_setpnt = self.__controls[data['Control_hold_at_setpnt']]
                else:
                    ctrl_hold_at_setpnt = None

                hw_source = StorageTank(
                    data['volume'],
                    data['daily_losses'],
                    data['min_temp'],
                    data['setpoint_temp'],
                    cold_water_source,
                    self.__simtime,
                    heat_source_dict,
                    primary_pipework,
                    energy_supply_unmet_demand.connection(name),
                    ctrl_hold_at_setpnt,
                    )
                energy_supply_conn_names.append(name)

                for heat_source_name, heat_source_data in data['HeatSource'].items():
                    energy_supply_name = heat_source_data['EnergySupply']
                    if energy_supply_name in diverters \
                    and diverters[energy_supply_name]['StorageTank'] == name \
                    and diverters[energy_supply_name]['HeatSource'] == heat_source_name:
                        energy_supply = self.__energy_supplies[heat_source_data['EnergySupply']]
                        pv_diverter = PVDiverter(hw_source, heat_source)
                        energy_supply.connect_diverter(pv_diverter)
                        self.__diverters.append(pv_diverter)

            elif hw_source_type == 'CombiBoiler':
                energy_supply_conn_name = data['HeatSourceWet'] + '_water_heating'
                energy_supply_conn_names.append(energy_supply_conn_name)
                cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
                hw_source = self.__heat_sources_wet[data['HeatSourceWet']].create_service_hot_water_combi(
                    data,
                    energy_supply_conn_name,
                    60, # TODO Remove hard-coding of HW temp
                    cold_water_source
                    )
            elif hw_source_type == 'PointOfUse':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn_name = name
                energy_supply_conn_names.append(energy_supply_conn_name)
                energy_supply_conn = energy_supply.connection(name)

                cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
                hw_source = PointOfUse(
                    data['power'],
                    data['efficiency'],
                    energy_supply_conn,
                    self.__simtime,
                    cold_water_source
                )
            elif hw_source_type == 'HIU':
                energy_supply_conn_name = data['HeatSourceWet'] + '_water_heating'
                energy_supply_conn_names.append(energy_supply_conn_name)
                cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
                hw_source = self.__heat_sources_wet[data['HeatSourceWet']].create_service_hot_water_direct(
                    energy_supply_conn_name,
                    60, # TODO Remove hard-coding of HW temp
                    cold_water_source,
                    )
            elif hw_source_type == 'HeatBattery':
                # TODO MC - add PCM heat battery in here
                pass
            else:
                sys.exit(name + ': hot water source type (' + hw_source_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return hw_source, energy_supply_conn_names

        self.__hot_water_sources = {}
        self.__energy_supply_conn_names_for_hot_water_source = {}
        for name, data in proj_dict['HotWaterSource'].items():
            self.__hot_water_sources[name], \
                self.__energy_supply_conn_names_for_hot_water_source[name] \
                = dict_to_hot_water_source(name, data)

        # Some systems (e.g. exhaust air heat pumps) may require overventilation
        # so initialise an empty list to hold the names of these systems
        self.__heat_system_names_requiring_overvent = []

        def dict_to_space_heat_system(name, data):
            space_heater_type = data['type']
            # ElecStorageHeater needs extra controllers
            if space_heater_type == 'ElecStorageHeater' and 'ControlCharger' in data.keys():
                charge_control = self.__controls[data['ControlCharger']]

            if 'Control' in data.keys():
                ctrl = self.__controls[data['Control']]
                # TODO Need to handle error if Control name is invalid.
            else:
                ctrl = None

            if space_heater_type == 'InstantElecHeater':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn_name = name
                energy_supply_conn = energy_supply.connection(name)

                space_heater = InstantElecHeater(
                    data['rated_power'],
                    data['frac_convective'],
                    energy_supply_conn,
                    self.__simtime,
                    ctrl,
                    )
            elif space_heater_type == 'ElecStorageHeater':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn_name = name
                energy_supply_conn = energy_supply.connection(name)

                space_heater = ElecStorageHeater(
                    data['rated_power'],
                    data['rated_power_instant'],
                    data['air_flow_type'],
                    data['temp_dis_safe'],
                    data['thermal_mass'],
                    data['frac_convective'],
                    data['U_ins'],
                    data['temp_charge_cut'],
                    data['mass_core'],
                    data['c_pcore'],
                    data['temp_core_target'],
                    data['A_core'],
                    data['c_wall'],
                    data['n_wall'],
                    data['thermal_mass_wall'],
                    data['fan_pwr'],
                    data['n_units'],
                    self.__zones[data['Zone']],
                    energy_supply_conn,
                    self.__simtime,
                    ctrl,
                    charge_control,
                )
            elif space_heater_type == 'WetDistribution':
                energy_supply_conn_name = data['HeatSource']['name'] + '_space_heating: ' + name
                heat_source = self.__heat_sources_wet[data['HeatSource']['name']]
                if isinstance(heat_source, HeatPump):
                    heat_source_service = heat_source.create_service_space_heating(
                        energy_supply_conn_name,
                        data['HeatSource']['temp_flow_limit_upper'],
                        data['temp_diff_emit_dsgn'],
                        ctrl,
                        )
                    if heat_source.source_is_exhaust_air():
                        # Record heating system as potentially requiring overventilation
                        self.__heat_system_names_requiring_overvent.append(name)

                elif isinstance(heat_source, Boiler):
                    heat_source_service = heat_source.create_service_space_heating(
                        energy_supply_conn_name,
                        ctrl,
                        )
                elif isinstance(heat_source, HeatNetwork):
                    heat_source_service = heat_source.create_service_space_heating(
                        energy_supply_conn_name,
                        ctrl,
                        )
                elif isinstance(heat_source, HeatBattery):
                    heat_source_service = heat_source.create_service_space_heating(
                        energy_supply_conn_name,
                        ctrl,
                        )
                else:
                    sys.exit(name + ': HeatSource type not recognised')
                    # TODO Exit just the current case instead of whole program entirely?

                space_heater = Emitters(
                    data['thermal_mass'],
                    data['c'],
                    data['n'],
                    data['temp_diff_emit_dsgn'],
                    data['frac_convective'],
                    heat_source_service,
                    self.__zones[data['Zone']],
                    self.__external_conditions,
                    data['ecodesign_controller'],
                    data['design_flow_temp'],
                    self.__simtime,
                    )
            elif space_heater_type == 'WarmAir':
                energy_supply_conn_name = data['HeatSource']['name'] + '_space_heating: ' + name
                heat_source = self.__heat_sources_wet[data['HeatSource']['name']]
                if isinstance(heat_source, HeatPump):
                    space_heater = heat_source.create_service_space_heating_warm_air(
                        energy_supply_conn_name,
                        ctrl,
                        data['frac_convective']
                        )
                    if heat_source.source_is_exhaust_air():
                        # Record heating system as potentially requiring overventilation
                        self.__heat_system_names_requiring_overvent.append(name)
                else:
                    sys.exit(name + ': HeatSource type not recognised')
                    # TODO Exit just the current case instead of whole program entirely?
            else:
                sys.exit(name + ': space heating system type (' \
                       + space_heater_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?

            return space_heater, energy_supply_conn_name

        # If one or more space heating systems have been provided, add them to the project
        self.__space_heat_systems = {}
        self.__energy_supply_conn_name_for_space_heat_system = {}
        # If no space heating systems have been provided, then skip. This
        # facilitates running the simulation with no heating systems at all
        if 'SpaceHeatSystem' in proj_dict:
            for name, data in proj_dict['SpaceHeatSystem'].items():
                # Only initialise systems that are actually used
                if name not in self.__heat_system_name_for_zone.values():
                    # TODO Add warning message here. Not adding now because it may break web interface
                    pass
                else:
                    self.__space_heat_systems[name], \
                        self.__energy_supply_conn_name_for_space_heat_system[name] \
                        = dict_to_space_heat_system(name, data)

        def dict_to_space_cool_system(name, data):
            if 'Control' in data.keys():
                ctrl = self.__controls[data['Control']]
                # TODO Need to handle error if Control name is invalid.
            else:
                ctrl = None

            cooling_system_type = data['type']
            if cooling_system_type == 'AirConditioning':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn_name = name
                energy_supply_conn = energy_supply.connection(name)

                cooling_system = AirConditioning(
                   data['cooling_capacity'],
                   data['efficiency'],
                   data['frac_convective'],
                   energy_supply_conn,
                   self.__simtime,
                   ctrl,
                   )
            else:
                sys.exit(name + ': CoolSystem type not recognised')

            return cooling_system, energy_supply_conn_name

        self.__space_cool_systems = {}
        self.__energy_supply_conn_name_for_space_cool_system = {}
        # If no space cooling systems have been provided, then skip. This
        # facilitates running the simulation with no cooling systems at all
        if 'SpaceCoolSystem' in proj_dict:
            for name, data in proj_dict['SpaceCoolSystem'].items():
                # Only initialise systems that are actually used
                if name not in self.__cool_system_name_for_zone.values():
                    # TODO Add warning message here. Not adding now because it may break web interface
                    pass
                else:
                    self.__space_cool_systems[name], \
                        self.__energy_supply_conn_name_for_space_cool_system[name] \
                        = dict_to_space_cool_system(name, data)

        def dict_to_on_site_generation(name, data):
            """ Parse dictionary of on site generation data and
                return approprate on site generation object """
            on_site_generation_type = data['type']
            if on_site_generation_type == 'PhotovoltaicSystem':

                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                pv_system = PhotovoltaicSystem(
                    data['peak_power'],
                    data['ventilation_strategy'],
                    data['pitch'],
                    self.__init_orientation(data['orientation360']),
                    data['base_height'], 
                    data['height'],
                    data['width'],
                    self.__external_conditions,
                    energy_supply_conn,
                    self.__simtime,
                    )
            else:
                sys.exit(name + ': on site generation type ('
                         + on_site_generation_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return pv_system

        self.__on_site_generation = {}
        # If no on site generation have been provided, then skip.
        if 'OnSiteGeneration' in proj_dict:
            for name, data in proj_dict['OnSiteGeneration'].items():
                self.__on_site_generation[name] = dict_to_on_site_generation(name, data)

    def __init_resistance_or_uvalue(self, name, data):
        """ Return thermal resistance of construction (r_c) based on alternative inputs

        User will either provide r_c directly or provide u_value which needs to be converted
        """
        # If r_c has been provided directly, then use it, and print warning if
        # u_value has been provided in addition
        if 'r_c' in data.keys():
            if 'u_value' in data.keys():
                print( 'Warning: For BuildingElement input object "' \
                     + name + '" both r_c and u_value have been provided. ' \
                     + 'The value for r_c will be used.' \
                     )
            return data['r_c']
        # If only u_value has been provided, use it to calculate r_c
        else:
            if 'u_value' in data.keys():
                return BuildingElement.convert_uvalue_to_resistance(data['u_value'], data['pitch'])
            else:
                sys.exit( 'Error: For BuildingElement input object "' \
                        + name + '" neither r_c nor u_value have been provided.' \
                        )

    def __init_orientation(self, orientation360):
        """ Convert orientation from 0-360 (clockwise) to -180 to +180 (anticlockwise) """
        return 180 - orientation360

    def total_floor_area(self):
        return self.__total_floor_area

    def calc_HTC_HLP(self):
        """ Calculate heat transfer coefficient (HTC) and heat loss parameter (HLP)
        according to the SAP10.2 specification """

        HTC_dict = {}
        HLP_dict = {}

        # Calculate the total fabric heat loss, total heat capacity, total ventilation heat
        # loss and total heat transfer coeffient for thermal bridges across all zones
        for z_name, zone in self.__zones.items():
            fabric_heat_loss = zone.total_fabric_heat_loss()
            thermal_bridges = zone.total_thermal_bridges()
            vent_heat_loss = zone.total_vent_heat_loss()

            # Calculate the heat transfer coefficent (HTC), in W / K
            # TODO check ventilation losses are correct
            HTC = fabric_heat_loss + thermal_bridges + vent_heat_loss

            # Calculate the HLP, in W / m2 K
            HLP = HTC / zone.area()

            HTC_dict[z_name] = HTC
            HLP_dict[z_name] = HLP

        total_HTC = sum(HTC_dict.values())
        total_HLP = total_HTC / self.__total_floor_area
        
        return total_HTC, total_HLP, HTC_dict, HLP_dict

    def calc_HCP(self):
        """ Calculate the total heat capacity normalised for floor area """
        # TODO party walls and solid doors should be exluded according to SAP spec - if party walls are
        # assumed to be ZTU building elements this could be set to zero?

        # Initialise variable
        total_heat_capacity = 0

        # Calculate the total heat capacity and total zone area
        for z_name, zone in self.__zones.items():
            total_heat_capacity += zone.total_heat_capacity()

        # Calculate the thermal mass parameter, in kJ / m2 K
        HCP = total_heat_capacity / self.__total_floor_area

        return HCP

    def calc_HLFF(self):
        "Calculate the heat loss form factor, defined as exposed area / floor area"

        total_heat_loss_area = 0
        for z_name, zone in self.__zones.items():
            total_heat_loss_area += zone.total_heat_loss_area()
        HLFF = total_heat_loss_area / self.__total_floor_area
        return HLFF

    def temp_internal_air(self):
        # Initialise internal air temperature and total area of all zones
        internal_air_temperature = 0

        # TODO here we are treating overall indoor temperature as average of all zones
        for z_name, zone in self.__zones.items():
            internal_air_temperature += zone.temp_internal_air() * zone.volume()

        internal_air_temperature /= self.__total_volume # average internal temperature
        return internal_air_temperature

    def __pipework_losses_and_internal_gains_from_hw(
            self,
            delta_t_h,
            vol_hot_water_at_tapping_point,
            hw_duration,
            no_of_hw_events,
            ):
        frac_dhw_energy_internal_gains = 0.25

        pw_losses_internal, pw_losses_external \
            = self.__calc_pipework_losses(
                delta_t_h,
                hw_duration,
                no_of_hw_events,
                )

        gains_internal_dhw_use \
            = frac_dhw_energy_internal_gains \
            * misc.water_demand_to_kWh(
                vol_hot_water_at_tapping_point,
                52.0, # TODO Hot water temperature - define this centrally
                self.temp_internal_air(),
                )

        # Return:
        # - losses from internal distribution pipework (kWh)
        # - losses from external distribution pipework (kWh)
        # - internal gains due to hot water use (kWh)
        return pw_losses_internal, pw_losses_external, gains_internal_dhw_use

    def __calc_pipework_losses(self, delta_t_h, hw_duration, no_of_hw_events):
        # sum up all hw_demand and allocate pipework losses also.
        # hw_demand is volume.

        # TODO demand water temperature is 52 as elsewhere, need to set it somewhere
        demand_water_temperature = 52
        internal_air_temperature = self.temp_internal_air()
        external_air_temperature = self.__external_conditions.air_temp()

        return self.__dhw_demand.calc_pipework_losses(
            delta_t_h,
            hw_duration,
            no_of_hw_events,
            demand_water_temperature,
            internal_air_temperature,
            external_air_temperature,
            )

    def run(self):
        """ Run the simulation """

        def calc_ductwork_losses(t_idx, delta_t_h, efficiency):
            """ Calculate the losses/gains in the MVHR ductwork

            Arguments:
            t_idx -- timestep index/count
            delta_t_h -- calculation timestep, in hours
            efficiency - MVHR heat recovery efficiency
            """
            # assume 100% efficiency 
            # i.e. temp inside the supply and extract ducts is room temp and temp inside exhaust and intake is external temp
            # assume MVHR unit is running 100% of the time

            internal_air_temperature = self.temp_internal_air()

            # Calculate heat loss from ducts when unit is inside
            # Air temp inside ducts increases, heat lost from dwelling
            ductwork = self.__space_heating_ductwork
            if ductwork == None:
                return 0

            ductwork_watts_heat_loss = 0.0

            # MVHR duct temperatures:
            # extract_duct_temp - indoor air temperature 
            # intake_duct_temp - outside air temperature
            
            temp_diff = internal_air_temperature - self.__external_conditions.air_temp()
            
            # Supply duct contains what the MVHR could recover
            supply_duct_temp = self.__external_conditions.air_temp() + (efficiency * temp_diff)
            
            # Exhaust duct contans the heat that couldn't be recovered
            exhaust_duct_temp = self.__external_conditions.air_temp() + ((1- efficiency) * temp_diff)
            
            ductwork_watts_heat_loss = \
                ductwork.total_duct_heat_loss(
                internal_air_temperature,
                supply_duct_temp,
                internal_air_temperature,
                self.__external_conditions.air_temp(),
                exhaust_duct_temp,
                efficiency)

            return ductwork_watts_heat_loss # heat loss in Watts for the timestep

        def calc_space_heating(delta_t_h, gains_internal_dhw):
            """ Calculate space heating demand, heating system output and temperatures

            Arguments:
            delta_t_h -- calculation timestep, in hours
            gains_internal_dhw -- internal gains from hot water system for this timestep, in W
            """
            temp_ext_air = self.__external_conditions.air_temp()
            # Calculate timestep in seconds
            delta_t = delta_t_h * units.seconds_per_hour

            ductwork_losses, ductwork_losses_per_m3 = 0.0, 0.0
            # ductwork gains/losses only for MVHR
            if isinstance(self.__ventilation, MechnicalVentilationHeatRecovery):
                ductwork_losses = calc_ductwork_losses(0, delta_t_h, self.__ventilation.efficiency())
                ductwork_losses_per_m3 = ductwork_losses / self.__total_volume

            # Calculate internal and solar gains for each zone
            gains_internal_zone = {}
            gains_solar_zone = {}
            for z_name, zone in self.__zones.items():
                # Initialise to dhw internal gains split proportionally to zone floor area
                gains_internal_zone_inner = gains_internal_dhw * zone.area() / self.__total_floor_area
                for internal_gains_name, internal_gains_object in self.__internal_gains.items():
                    gains_internal_zone_inner\
                        += internal_gains_object.total_internal_gain(zone.area())
                gains_internal_zone[z_name] = gains_internal_zone_inner
                # Add gains from ventilation fans (also calculates elec demand from fans)
                # TODO Remove the branch on the type of ventilation (find a better way)
                if self.__ventilation is not None \
                and not isinstance(self.__ventilation, NaturalVentilation):
                    gains_internal_zone[z_name] += self.__ventilation.fans(zone.volume())
                    gains_internal_zone[z_name] += ductwork_losses_per_m3 * zone.volume()

                gains_solar_zone[z_name] = zone.gains_solar()

            # Calculate space heating and cooling demand for each zone and sum
            # Keep track of how much is from each zone, so that energy provided
            # can be split between them in same proportion later
            space_heat_demand_system, space_cool_demand_system, \
                space_heat_demand_zone, space_cool_demand_zone, h_ve_cool_extra_zone \
                = self.__space_heat_cool_demand_by_system_and_zone(
                    delta_t_h,
                    temp_ext_air,
                    gains_internal_zone,
                    gains_solar_zone,
                    )

            # If any heating systems potentially require overventilation,
            # calculate running time and throughput factor for all services
            # combined based on space heating demand assuming no overventilation
            space_heat_running_time_cumulative = 0.0
            throughput_factor = 1.0
            for heat_system_name, heat_system in self.__space_heat_systems.items():
                if heat_system_name in self.__heat_system_names_requiring_overvent:
                    space_heat_running_time_cumulative, throughput_factor \
                        = heat_system.running_time_throughput_factor(
                            space_heat_demand_system[heat_system_name],
                            space_heat_running_time_cumulative,
                            )

            # If there is overventilation due to heating or hot water system (e.g.
            # exhaust air heat pump) then recalculate space heating/cooling demand
            # with additional ventilation calculated based on throughput factor
            # based on original space heating demand calculation. Note the
            # additional ventilation throughput is the result of the HP running
            # to satisfy both space and water heating demand but will affect
            # space heating demand only
            # TODO The space heating demand is only recalculated once, rather
            #      than feeding back in to the throughput factor calculation
            #      above to get a further-refined space heating demand. This is
            #      consistent with the approach in SAP 10.2 and keeps the
            #      execution time of the calculation bounded. However, the
            #      merits of iterating over this calculation until converging on
            #      a solution should be considered in the future.
            if throughput_factor > 1.0:
                for z_name, zone in self.__zones.items():
                    # Add additional gains from ventilation fans
                    # TODO Remove the branch on the type of ventilation (find a better way)
                    if self.__ventilation is not None \
                    and not isinstance(self.__ventilation, NaturalVentilation):
                        gains_internal_zone[z_name] \
                            += self.__ventilation.fans(zone.volume(), throughput_factor - 1.0)
                space_heat_demand_system, space_cool_demand_system, \
                    space_heat_demand_zone, space_cool_demand_zone, h_ve_cool_extra_zone \
                    = self.__space_heat_cool_demand_by_system_and_zone(
                        delta_t_h,
                        temp_ext_air,
                        gains_internal_zone,
                        gains_solar_zone,
                        throughput_factor,
                        )

            # Calculate how much heating the systems can provide
            space_heat_provided = {}
            for heat_system_name, heat_system in self.__space_heat_systems.items():
                space_heat_provided[heat_system_name] = \
                    heat_system.demand_energy(space_heat_demand_system[heat_system_name])

            # Calculate how much cooling the systems can provide
            space_cool_provided = {}
            for cool_system_name, cool_system in self.__space_cool_systems.items():
                space_cool_provided[cool_system_name] = \
                    cool_system.demand_energy(space_cool_demand_system[cool_system_name])

            # Apportion the provided heating/cooling between the zones in
            # proportion to the heating/cooling demand in each zone. Then
            # update resultant temperatures in zones.
            internal_air_temp = {}
            operative_temp = {}
            heat_balance_dict = {}
            for z_name, zone in self.__zones.items():
                # Look up names of relevant heating and cooling systems for this zone
                h_name = self.__heat_system_name_for_zone[z_name]
                c_name = self.__cool_system_name_for_zone[z_name]

                # If zone is unheated or there was no demand on heating system,
                # set heating gains for zone to zero, else calculate
                # TODO Commented-out code in the block below was used to
                #      apportion the delivered heating between the zones that
                #      are served by the system in question, in proportion to
                #      demand from each zone. However, this does not work when
                #      the demand is zero but the system is delivering heating
                #      anyway, e.g. as may be the case with radiators cooling
                #      down at the end of a heating period. Therefore, for now
                #      assume that each system only serves a single zone (for
                #      systems such as boiler feeding radiators, this means one
                #      emitter system for each zone, but they can all be served
                #      by the same boiler).
                if h_name is None: # or space_heat_demand_system[h_name] == 0.0:
                    gains_heat = 0.0
                else:
                    # frac_heat_zone = space_heat_demand_zone[z_name] \
                    #                / space_heat_demand_system[h_name]
                    # gains_heat = space_heat_provided[h_name] * frac_heat_zone
                    gains_heat = space_heat_provided[h_name]

                # If zone is uncooled or there was no demand on cooling system,
                # set cooling gains for zone to zero, else calculate
                # TODO Commented-out code in the block below was used to
                #      apportion the delivered cooling between the zones that
                #      are served by the system in question, in proportion to
                #      demand from each zone. However, this does not work when
                #      the demand is zero but the system is delivering cooling
                #      anyway. Therefore, for now assume that each system only
                #      serves a single zone.
                if c_name is None: # or space_cool_demand_system[c_name] == 0.0:
                    gains_cool = 0.0
                else:
                    # frac_cool_zone = space_cool_demand_zone[z_name] \
                    #                / space_cool_demand_system[c_name]
                    # gains_cool = space_cool_provided[c_name] * frac_cool_zone
                    gains_cool = space_cool_provided[c_name]

                # Sum heating gains (+ve) and cooling gains (-ve) and convert from kWh to W
                gains_heat_cool = (gains_heat + gains_cool) * units.W_per_kW / delta_t_h

                # Calculate how much space heating / cooling demand is unmet
                # Note: Demand is not considered unmet if it is outside the
                #       required heating/cooling period (which does not include
                #       times when the system is on due to setback or advanced
                #       start)
                # Note: Need to check that demand is non-zero, to avoid
                #       reporting unmet demand when heating system is absorbing
                #       energy from zone or cooling system is releasing energy
                #       to zone, which may be the case in some timesteps for
                #       systems with significant thermal mass.
                in_req_heat_period \
                    = False if h_name is None \
                      else self.__space_heat_systems[h_name].in_required_period()
                if in_req_heat_period and space_heat_demand_zone[z_name] > 0:
                    energy_shortfall_heat = max(0, space_heat_demand_zone[z_name] - gains_heat)
                    self.__energy_supply_conn_unmet_demand_zone[z_name].demand_energy(energy_shortfall_heat)
                in_req_cool_period \
                    = False if c_name is None \
                      else self.__space_cool_systems[c_name].in_required_period()
                if in_req_cool_period and space_cool_demand_zone[z_name] < 0:
                    energy_shortfall_cool = max(0, - (space_cool_demand_zone[z_name] - gains_cool))
                    self.__energy_supply_conn_unmet_demand_zone[z_name].demand_energy(energy_shortfall_cool)

                # Look up convective fraction for heating/cooling for this zone
                # Note: gains_heat could be negative (or gains_cool could be
                #       positive) if thermal mass of emitters causes e.g. the
                #       heat emitters to absorb energy from the zone.
                if gains_heat != 0:
                    # Note: If h_name is None then there will be a KeyError
                    # exception in the line below, but this should not happen as
                    # gains_heat != 0 should only occur if a heating system
                    # has been defined.
                    frac_convective = self.__space_heat_systems[h_name].frac_convective()
                elif gains_cool != 0:
                    # Note: If c_name is None then there will be a KeyError
                    # exception in the line below, but this should not happen as
                    # gains_cool != 0 should only occur if a cooling system
                    # has been defined.
                    frac_convective = self.__space_cool_systems[c_name].frac_convective()
                else:
                    frac_convective = 1.0

                heat_balance_dict[z_name] = zone.update_temperatures(
                    delta_t,
                    temp_ext_air,
                    gains_internal_zone[z_name],
                    gains_solar_zone[z_name],
                    gains_heat_cool,
                    frac_convective,
                    vent_extra_h_ve = h_ve_cool_extra_zone[z_name],
                    throughput_factor = throughput_factor,
                    )
                
                if h_name is None:
                    space_heat_demand_system[h_name] = 0.0
                    space_heat_provided[h_name] = 0.0
                if c_name is None:
                    space_cool_demand_system[c_name] = 0.0
                    space_cool_provided[c_name] = 0.0

                internal_air_temp[z_name] = zone.temp_internal_air()
                operative_temp[z_name] = zone.temp_operative()

            return gains_internal_zone, gains_solar_zone, \
                   operative_temp, internal_air_temp, \
                   space_heat_demand_zone, space_cool_demand_zone, \
                   space_heat_demand_system, space_cool_demand_system, \
                   space_heat_provided, space_cool_provided, \
                   ductwork_losses, heat_balance_dict

        timestep_array = []
        gains_internal_dict = {}
        gains_solar_dict = {}
        operative_temp_dict = {}
        internal_air_temp_dict = {}
        space_heat_demand_dict = {}
        space_cool_demand_dict = {}
        space_heat_demand_system_dict = {}
        space_cool_demand_system_dict = {}
        space_heat_provided_dict = {}
        space_cool_provided_dict = {}
        zone_list = []
        hot_water_demand_dict = {}
        hot_water_energy_demand_dict = {}
        hot_water_energy_demand_dict_incl_pipework = {}
        hot_water_energy_output_dict = {}
        hot_water_duration_dict = {}
        hot_water_no_events_dict = {}
        hot_water_pipework_dict = {}
        ductwork_gains_dict = {}
        heat_balance_all_dict = {'air_node': {}, 'internal_boundary': {},'external_boundary': {}}
        heat_source_wet_results_dict = {}
        heat_source_wet_results_annual_dict = {}

        for z_name in self.__zones.keys():
            gains_internal_dict[z_name] = []
            gains_solar_dict[z_name] = []
            operative_temp_dict[z_name] = []
            internal_air_temp_dict[z_name] = []
            space_heat_demand_dict[z_name] = []
            space_cool_demand_dict[z_name] = []
            zone_list.append(z_name)
            for hb_name in heat_balance_all_dict.keys():
                heat_balance_all_dict[hb_name][z_name] = {}

        for z_name, h_name in self.__heat_system_name_for_zone.items():
            space_heat_demand_system_dict[h_name] = []
            space_heat_provided_dict[h_name] = []

        for z_name, c_name in self.__cool_system_name_for_zone.items():
            space_cool_demand_system_dict[c_name] = []
            space_cool_provided_dict[c_name] = []

        hot_water_demand_dict['demand'] = []
        hot_water_energy_demand_dict['energy_demand'] = []
        hot_water_energy_demand_dict_incl_pipework['energy_demand_incl_pipework_loss'] = []
        hot_water_energy_output_dict['energy_output'] = []
        hot_water_duration_dict['duration'] = []
        hot_water_no_events_dict['no_events'] = []
        hot_water_pipework_dict['pw_losses'] = []
        ductwork_gains_dict['ductwork_gains'] = []

        # Loop over each timestep
        for t_idx, t_current, delta_t_h in self.__simtime:
            timestep_array.append(t_current)
            hw_demand_vol, hw_vol_at_tapping_points, hw_duration, no_events, \
                hw_energy_demand \
                = self.__dhw_demand.hot_water_demand(t_idx)

            # Convert from litres to kWh
            cold_water_source = self.__hot_water_sources['hw cylinder'].get_cold_water_source()
            cold_water_temperature = cold_water_source.temperature()
            hw_energy_demand_incl_pipework_loss = misc.water_demand_to_kWh(
                hw_demand_vol,
                52.0, # Assumed hot water temperature. TODO Need to define/calculate this centrally.
                cold_water_temperature,
                )

            hw_energy_output \
                = self.__hot_water_sources['hw cylinder'].demand_hot_water(hw_demand_vol)
            # TODO Remove hard-coding of hot water source name
            # TODO Reporting of the hot water energy output assumes that there
            #      is only one water heating system. If the model changes in
            #      future to allow more than one hot water system, this code may
            #      need to be revised to handle that scenario.

            pw_losses_internal, pw_losses_external, gains_internal_dhw_use \
                = self.__pipework_losses_and_internal_gains_from_hw(
                    delta_t_h,
                    hw_vol_at_tapping_points,
                    hw_duration,
                    no_events,
                    )

            gains_internal_dhw \
                = (pw_losses_internal + gains_internal_dhw_use) \
                * units.W_per_kW / self.__simtime.timestep()
            if isinstance(self.__hot_water_sources['hw cylinder'], StorageTank) \
            or isinstance(self.__hot_water_sources['hw cylinder'], BoilerServiceWaterCombi):
                gains_internal_dhw += self.__hot_water_sources['hw cylinder'].internal_gains()

            gains_internal_zone, gains_solar_zone, \
                operative_temp, internal_air_temp, \
                space_heat_demand_zone, space_cool_demand_zone, \
                space_heat_demand_system, space_cool_demand_system, \
                space_heat_provided, space_cool_provided, \
                ductwork_gains, heat_balance_dict \
                = calc_space_heating(delta_t_h, gains_internal_dhw)

            # Perform calculations that can only be done after all heating
            # services have been calculated.
            for system in self.__timestep_end_calcs:
                system.timestep_end()

            for z_name, gains_internal in gains_internal_zone.items():
                gains_internal_dict[z_name].append(gains_internal)

            for z_name, gains_solar in gains_solar_zone.items():
                gains_solar_dict[z_name].append(gains_solar)

            for z_name, temp in operative_temp.items():
                operative_temp_dict[z_name].append(temp)

            for z_name, temp in internal_air_temp.items():
                internal_air_temp_dict[z_name].append(temp)

            for z_name, demand in space_heat_demand_zone.items():
                space_heat_demand_dict[z_name].append(demand)

            for z_name, demand in space_cool_demand_zone.items():
                space_cool_demand_dict[z_name].append(demand)

            for h_name, demand in space_heat_demand_system.items():
                space_heat_demand_system_dict[h_name].append(demand)

            for c_name, demand in space_cool_demand_system.items():
                space_cool_demand_system_dict[c_name].append(demand)

            for h_name, output in space_heat_provided.items():
                space_heat_provided_dict[h_name].append(output)

            for c_name, output in space_cool_provided.items():
                space_cool_provided_dict[c_name].append(output)

            for z_name, hb_dict in heat_balance_dict.items():
                if hb_dict is not None:
                    for hb_name, gains_losses_dict in hb_dict.items():
                        for heat_gains_losses_name, heat_gains_losses_value in gains_losses_dict.items():
                            if heat_gains_losses_name in heat_balance_all_dict[hb_name][z_name].keys():
                                heat_balance_all_dict[hb_name][z_name][heat_gains_losses_name].append(heat_gains_losses_value)
                            else:
                                heat_balance_all_dict[hb_name][z_name][heat_gains_losses_name] =[heat_gains_losses_value]

            hot_water_demand_dict['demand'].append(hw_demand_vol)
            hot_water_energy_demand_dict['energy_demand'].append(hw_energy_demand)
            hot_water_energy_demand_dict_incl_pipework['energy_demand_incl_pipework_loss'].append(hw_energy_demand_incl_pipework_loss)
            hot_water_energy_output_dict['energy_output'].append(hw_energy_output)
            hot_water_duration_dict['duration'].append(hw_duration)
            hot_water_no_events_dict['no_events'].append(no_events)
            hot_water_pipework_dict['pw_losses'].append(pw_losses_internal + pw_losses_external)
            ductwork_gains_dict['ductwork_gains'].append(ductwork_gains)

            #loop through on-site energy generation
            for g_name, gen in self.__on_site_generation.items():
                # Get energy produced for the current timestep
                self.__on_site_generation[g_name].produce_energy()

            for _, supply in self.__energy_supplies.items():
                supply.calc_energy_import_export_betafactor()

            for diverter in self.__diverters:
                diverter.timestep_end()

        zone_dict = {
            'Internal gains': gains_internal_dict,
            'Solar gains': gains_solar_dict,
            'Operative temp': operative_temp_dict,
            'Internal air temp': internal_air_temp_dict,
            'Space heat demand': space_heat_demand_dict,
            'Space cool demand': space_cool_demand_dict,
            }
        hc_system_dict = {
            'Heating system': space_heat_demand_system_dict,
            'Cooling system': space_cool_demand_system_dict,
            'Heating system output': space_heat_provided_dict,
            'Cooling system output': space_cool_provided_dict,
            }
        hot_water_dict = {
            'Hot water demand': hot_water_demand_dict,
            'Hot water energy demand': hot_water_energy_demand_dict,
            'Hot water energy demand incl pipework_loss': hot_water_energy_demand_dict_incl_pipework,
            'Hot water duration': hot_water_duration_dict,
            'Hot Water Events': hot_water_no_events_dict,
            'Pipework losses': hot_water_pipework_dict,
            }

        # Report detailed outputs from heat source wet objects, if requested and available
        # TODO Note that the below assumes that there is only one water
        #      heating service and therefore that all hot water energy
        #      output is assigned to that service. If the model changes in
        #      future to allow more than one hot water system, this code may
        #      need to be revised to handle that scenario.
        if self.__detailed_output_heating_cooling:
            for name, heat_source_wet in self.__heat_sources_wet.items():
                if  hasattr(heat_source_wet, "output_detailed_results") \
                and callable(heat_source_wet.output_detailed_results):
                    heat_source_wet_results_dict[name], heat_source_wet_results_annual_dict[name] \
                        = heat_source_wet.output_detailed_results(
                            hot_water_energy_output_dict['energy_output']
                            )

        # Return results from all energy supplies
        results_totals = {}
        results_end_user = {}
        energy_import = {}
        energy_export = {}
        energy_generated_consumed = {}
        energy_to_storage = {}
        energy_from_storage = {}
        energy_diverted = {}
        betafactor = {}
        for name, supply in self.__energy_supplies.items():
            results_totals[name] = supply.results_total()
            results_end_user[name] = supply.results_by_end_user()
            energy_import[name] = supply.get_energy_import()
            energy_export[name] = supply.get_energy_export()
            energy_generated_consumed[name] = supply.get_energy_generated_consumed()
            energy_to_storage[name], energy_from_storage[name] = supply.get_energy_to_from_battery()
            energy_diverted[name] = supply.get_energy_diverted()
            betafactor[name] = supply.get_beta_factor()

        hot_water_energy_out = {'hw cylinder': hot_water_energy_output_dict['energy_output']}
        dhw_cop_dict = self.__heat_cool_cop(
            hot_water_energy_out,
            results_end_user,
            self.__energy_supply_conn_names_for_hot_water_source,
            )
        heat_cop_dict = self.__heat_cool_cop(
            space_heat_provided_dict,
            results_end_user,
            self.__energy_supply_conn_name_for_space_heat_system
            )
        cool_cop_dict = self.__heat_cool_cop(
            space_cool_provided_dict,
            results_end_user,
            self.__energy_supply_conn_name_for_space_cool_system
            )

        return \
            timestep_array, results_totals, results_end_user, \
            energy_import, energy_export, energy_generated_consumed, \
            energy_to_storage, energy_from_storage, energy_diverted, betafactor, \
            zone_dict, zone_list, hc_system_dict, hot_water_dict, \
            heat_cop_dict, cool_cop_dict, dhw_cop_dict, \
            ductwork_gains_dict, heat_balance_all_dict, \
            heat_source_wet_results_dict, heat_source_wet_results_annual_dict

    def __heat_cool_cop(
            self,
            energy_provided_dict,
            results_end_user,
            energy_supply_conn_name_for_space_hc_system,
            ):
        """ Calculate overall CoP over calculation period for each heating and cooling system """
        # Loop over heating systems, get energy output and input, and calculate CoP
        hc_output_overall = {}
        hc_input_overall = {}
        cop_dict = {}
        for hc_name, hc_output in energy_provided_dict.items():
            if hc_name is None:
                continue
            # Take absolute value because cooling system output is reported as a negative value
            hc_output_overall[hc_name] = abs(sum(hc_output))
            hc_input_overall[hc_name] = 0.0
            energy_supply_conn_names = energy_supply_conn_name_for_space_hc_system[hc_name]
            if not isinstance(energy_supply_conn_names, list):
                energy_supply_conn_names = [energy_supply_conn_names]
            for fuel_name, fuel_summary in results_end_user.items():
                if fuel_name == '_unmet_demand':
                    continue
                for conn_name, energy_cons in fuel_summary.items():
                    if conn_name in energy_supply_conn_names:
                        hc_input_overall[hc_name] += sum(energy_cons)

            if hc_input_overall[hc_name] > 0:
                cop_dict[hc_name] = hc_output_overall[hc_name] / hc_input_overall[hc_name]
            else:
                cop_dict[hc_name] = 'DIV/0'

        return cop_dict

    def __space_heat_cool_demand_by_system_and_zone(
            self,
            delta_t_h,
            temp_ext_air,
            gains_internal_zone,
            gains_solar_zone,
            throughput_factor=1.0,
            ):
        """ Calculate space heating and cooling demand for each zone and sum.

        Keep track of how much is from each zone, so that energy provided
        can be split between them in same proportion later
        """
        space_heat_demand_system = {} # in kWh
        for heat_system_name in self.__space_heat_systems.keys():
            space_heat_demand_system[heat_system_name] = 0.0

        space_cool_demand_system = {} # in kWh
        for cool_system_name in self.__space_cool_systems.keys():
            space_cool_demand_system[cool_system_name] = 0.0

        space_heat_demand_zone = {}
        space_cool_demand_zone = {}
        h_ve_cool_extra_zone = {}
        for z_name, zone in self.__zones.items():
            # Look up names of relevant heating and cooling systems for this zone
            h_name = self.__heat_system_name_for_zone[z_name]
            c_name = self.__cool_system_name_for_zone[z_name]

            # Look up convective fraction for heating/cooling for this zone
            if h_name is not None:
                frac_convective_heat = self.__space_heat_systems[h_name].frac_convective()
                temp_setpnt_heat = self.__space_heat_systems[h_name].temp_setpnt()
            else:
                frac_convective_heat = 1.0
                temp_setpnt_heat = None
            if c_name is not None:
                frac_convective_cool = self.__space_cool_systems[c_name].frac_convective()
                temp_setpnt_cool = self.__space_cool_systems[c_name].temp_setpnt()
            else:
                frac_convective_cool = 1.0
                temp_setpnt_cool = None

            # Use default setpoints when there is no heat/cool system or
            # there is no setpoint for the current timestep
            if temp_setpnt_heat is None:
                # Set heating setpoint to absolute zero to ensure no heating demand
                temp_setpnt_heat = Kelvin2Celcius(0.0)
            if temp_setpnt_cool is None:
                # Set cooling setpoint to Planck temperature to ensure no cooling demand
                temp_setpnt_cool = Kelvin2Celcius(1.4e32)

            space_heat_demand_zone[z_name], space_cool_demand_zone[z_name], h_ve_cool_extra_zone[z_name] \
                = zone.space_heat_cool_demand(
                    delta_t_h,
                    temp_ext_air,
                    gains_internal_zone[z_name],
                    gains_solar_zone[z_name],
                    frac_convective_heat,
                    frac_convective_cool,
                    temp_setpnt_heat,
                    temp_setpnt_cool,
                    throughput_factor = throughput_factor,
                    )

            if h_name is not None: # If the zone is heated
                space_heat_demand_system[h_name] += space_heat_demand_zone[z_name]
            if c_name is not None: # If the zone is cooled
                space_cool_demand_system[c_name] += space_cool_demand_zone[z_name]

        return \
            space_heat_demand_system, space_cool_demand_system, \
            space_heat_demand_zone, space_cool_demand_zone, h_ve_cool_extra_zone

