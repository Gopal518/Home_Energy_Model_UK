#!/usr/bin/env python3

"""
This module provides functions to implement pre- and post-processing
steps for the Future Homes Standard.
"""

import math
import sys
import os
import json
import csv
from fractions import Fraction
from core import project, schedule, units
from core.water_heat_demand.misc import frac_hot_water
from cmath import log
from wrappers.future_homes_standard.FHS_HW_events import HW_event_adjust_allocate, HW_events_generator

this_directory = os.path.dirname(os.path.relpath(__file__))
FHSEMISFACTORS =  os.path.join(this_directory, "FHS_emisPEfactors_07-06-2023.csv")
emis_factor_name = 'Emissions Factor kgCO2e/kWh'
emis_oos_factor_name = 'Emissions Factor kgCO2e/kWh including out-of-scope emissions'
PE_factor_name = 'Primary Energy Factor kWh/kWh delivered'

energysupplyname_electricity = 'mains elec'

appl_obj_name = 'appliances'
elec_cook_obj_name = 'Eleccooking'
gas_cook_obj_name = 'Gascooking'
hw_timer_main_name = "hw timer"
hw_timer_hold_at_setpnt_name = "hw timer eco7"

livingroom_setpoint_fhs = 21.0
restofdwelling_setpoint_fhs = 20.0

simtime_start = 0
simtime_end = 8760
simtime_step = 0.5

def apply_fhs_preprocessing(project_dict):
    """ Apply assumptions and pre-processing steps for the Future Homes Standard """
    
    project_dict['SimulationTime']["start"] = simtime_start
    project_dict['SimulationTime']["end"] = simtime_end
    project_dict['SimulationTime']["step"] = simtime_step

    project_dict['InternalGains']={}
    
    TFA = calc_TFA(project_dict)
    
    nbeds = calc_nbeds(project_dict)
    
    try:
        N_occupants = calc_N_occupants(TFA, nbeds)
    except ValueError as e:
        sys.exit("Invalid data used in occupancy calculation. {0}".format(e))
    
    #construct schedules
    schedule_occupancy_weekday, schedule_occupancy_weekend = create_occupancy(N_occupants)
    create_metabolic_gains(
        project_dict,
        TFA, 
        schedule_occupancy_weekday, 
        schedule_occupancy_weekend)

    create_water_heating_pattern(project_dict)
    create_heating_pattern(project_dict)
    create_evaporative_losses(project_dict, TFA, N_occupants)
    create_lighting_gains(project_dict, TFA, N_occupants)
    create_cooking_gains(project_dict,TFA, N_occupants)
    create_appliance_gains(project_dict, TFA, N_occupants)
    
    for hwsource in project_dict["HotWaterSource"]:
        if project_dict["HotWaterSource"][hwsource]["type"] == "StorageTank":
            project_dict["HotWaterSource"][hwsource]["min_temp"] = 52.0
            project_dict["HotWaterSource"][hwsource]["setpoint_temp"] = 60.0
        
    cold_water_feed_temps = create_cold_water_feed_temps(project_dict)
    create_hot_water_use_pattern(project_dict, TFA, N_occupants, cold_water_feed_temps)
    create_cooling(project_dict)
    create_window_opening_schedule(project_dict)

    return project_dict

def load_emisPE_factors():
    """ Load emissions factors and primary energy factors from data file """
    emisPE_factors = {}
    with open(FHSEMISFACTORS, 'r') as emisPE_factors_csv:
        emisPE_factors_reader = csv.DictReader(emisPE_factors_csv, delimiter=',')

        for row in emisPE_factors_reader:
            if row["Fuel Code"]!= "":
                fuel_code = row["Fuel Code"]
                emisPE_factors[fuel_code] = row
                # Remove keys that aren't factors to be applied to results
                emisPE_factors[fuel_code].pop("Fuel Code")
                emisPE_factors[fuel_code].pop("Fuel")

    return emisPE_factors

def apply_fhs_postprocessing(
        project_dict,
        results_totals,
        energy_import,
        energy_export,
        results_end_user,
        timestep_array,
        file_path,
        notional,
        ):
    """ Post-process core simulation outputs as required for Future Homes Standard """
    no_of_timesteps = len(timestep_array)

    # Read factors from csv
    emisPE_factors = load_emisPE_factors()

    # Add unmet demand to list of EnergySupply objects
    project_dict["EnergySupply"]['_unmet_demand'] = {"fuel": "unmet_demand"}

    # For each EnergySupply object:
    # - look up relevant factors for import/export from csv or custom factors
    #   from input file
    # - look up relevant factors for generation from csv
    # - apply relevant factors for import, export and generation
    # Applying factors in this way rather than applying a net export factor to
    # exported energy accounts for energy generated and used on site and also
    # accounts for battery storage losses
    emis_results = {}
    emis_oos_results = {}
    PE_results = {}
    for energy_supply in project_dict["EnergySupply"]:
        emis_results[energy_supply] = {}
        emis_oos_results[energy_supply] = {}
        PE_results[energy_supply] = {}

        fuel_code = project_dict["EnergySupply"][energy_supply]["fuel"]

        # Get emissions/PE factors for import/export
        if fuel_code == "custom":
            emis_factor_import_export \
                = float(project_dict["EnergySupply"][energy_supply]["factor"][emis_factor_name])
            emis_oos_factor_import_export \
                = float(project_dict["EnergySupply"][energy_supply]["factor"][emis_oos_factor_name])
            PE_factor_import_export \
                = float(project_dict["EnergySupply"][energy_supply]["factor"][PE_factor_name])
        else:
            emis_factor_import_export = float(emisPE_factors[fuel_code][emis_factor_name])
            emis_oos_factor_import_export = float(emisPE_factors[fuel_code][emis_oos_factor_name])
            PE_factor_import_export = float(emisPE_factors[fuel_code][PE_factor_name])

        # Calculate energy imported and associated emissions/PE
        emis_results[energy_supply]['import'] = [
            x * emis_factor_import_export for x in energy_import[energy_supply]
            ]
        emis_oos_results[energy_supply]['import'] = [
            x * emis_oos_factor_import_export for x in energy_import[energy_supply]
            ]
        PE_results[energy_supply]['import'] = [
            x * PE_factor_import_export for x in energy_import[energy_supply]
            ]

        # If there is any export, Calculate energy exported and associated emissions/PE
        # Note that by convention, exported energy is negative
        if sum(energy_export[energy_supply]) < 0:
            emis_results[energy_supply]['export'] = [
                x * emis_factor_import_export for x in energy_export[energy_supply]
                ]
            emis_oos_results[energy_supply]['export'] = [
                x * emis_oos_factor_import_export for x in energy_export[energy_supply]
                ]
            PE_results[energy_supply]['export'] = [
                x * PE_factor_import_export for x in energy_export[energy_supply]
                ]
        else:
            emis_results[energy_supply]['export'] = [0.0] * no_of_timesteps
            emis_oos_results[energy_supply]['export'] = [0.0] * no_of_timesteps
            PE_results[energy_supply]['export'] = [0.0] * no_of_timesteps

        # Calculate energy generated and associated emissions/PE
        energy_generated = [0.0] * no_of_timesteps
        for end_user_name, end_user_energy in results_end_user[energy_supply].items():
            # If there is energy generation (represented as negative demand)
            if sum(end_user_energy) < 0.0:
                for t_idx in range(0, no_of_timesteps):
                    # Subtract here because generation is represented as negative demand
                    energy_generated[t_idx] -= end_user_energy[t_idx]

        if sum(energy_generated) > 0.0:
            # TODO Allow custom (user-defined) factors for generated energy?
            fuel_code_generated = fuel_code + '_generated'
            emis_factor_generated = float(emisPE_factors[fuel_code_generated][emis_factor_name])
            emis_oos_factor_generated = float(emisPE_factors[fuel_code_generated][emis_oos_factor_name])
            PE_factor_generated = float(emisPE_factors[fuel_code_generated][PE_factor_name])

            emis_results[energy_supply]['generated'] = [
                x * emis_factor_generated for x in energy_generated
                ]
            emis_oos_results[energy_supply]['generated'] = [
                x * emis_oos_factor_generated for x in energy_generated
                ]
            PE_results[energy_supply]['generated'] = [
                x * PE_factor_generated for x in energy_generated
                ]
        else:
            emis_results[energy_supply]['generated'] = [0.0] * no_of_timesteps
            emis_oos_results[energy_supply]['generated'] = [0.0] * no_of_timesteps
            PE_results[energy_supply]['generated'] = [0.0] * no_of_timesteps

        # Calculate unregulated energy demand and associated emissions/PE
        energy_unregulated = [0.0] * no_of_timesteps
        for end_user_name, end_user_energy in results_end_user[energy_supply].items():
            if end_user_name in (appl_obj_name, elec_cook_obj_name, gas_cook_obj_name):
                for t_idx in range(0, no_of_timesteps):
                    energy_unregulated[t_idx] += end_user_energy[t_idx]

        emis_results[energy_supply]['unregulated'] = [
            x * emis_factor_import_export for x in energy_unregulated
            ]
        emis_oos_results[energy_supply]['unregulated'] = [
            x * emis_oos_factor_import_export for x in energy_unregulated
            ]
        PE_results[energy_supply]['unregulated'] = [
            x * PE_factor_import_export for x in energy_unregulated
            ]

        # Calculate total CO2/PE for each EnergySupply based on import and export,
        # subtracting unregulated
        emis_results[energy_supply]['total'] = [0.0] * no_of_timesteps
        emis_oos_results[energy_supply]['total'] = [0.0] * no_of_timesteps
        PE_results[energy_supply]['total'] = [0.0] * no_of_timesteps
        for t_idx in range(0, no_of_timesteps):
            emis_results[energy_supply]['total'][t_idx] \
                = emis_results[energy_supply]['import'][t_idx] \
                + emis_results[energy_supply]['export'][t_idx] \
                + emis_results[energy_supply]['generated'][t_idx] \
                - emis_results[energy_supply]['unregulated'][t_idx]
            emis_oos_results[energy_supply]['total'][t_idx] \
                = emis_oos_results[energy_supply]['import'][t_idx] \
                + emis_oos_results[energy_supply]['export'][t_idx] \
                + emis_oos_results[energy_supply]['generated'][t_idx] \
                - emis_oos_results[energy_supply]['unregulated'][t_idx]
            PE_results[energy_supply]['total'][t_idx] \
                = PE_results[energy_supply]['import'][t_idx] \
                + PE_results[energy_supply]['export'][t_idx] \
                + PE_results[energy_supply]['generated'][t_idx] \
                - PE_results[energy_supply]['unregulated'][t_idx]

    # Calculate summary results
    TFA = calc_TFA(project_dict)
    total_emissions_rate = sum([sum(emis['total']) for emis in emis_results.values()]) / TFA
    total_PE_rate = sum([sum(PE['total']) for PE in PE_results.values()]) / TFA

    # Write results to output files
    write_postproc_file(file_path, "emissions", emis_results, no_of_timesteps)
    write_postproc_file(file_path, "emissions_incl_out_of_scope", emis_oos_results, no_of_timesteps)
    write_postproc_file(file_path, "primary_energy", PE_results, no_of_timesteps)
    write_postproc_summary_file(file_path, total_emissions_rate, total_PE_rate, notional)

def write_postproc_file(file_path, results_type, results, no_of_timesteps):
    file_name = file_path + 'postproc' + '_'+ results_type + '.csv'

    row_headers = []
    rows_results = []

    # Loop over each EnergySupply object and add headers and results to rows
    for energy_supply, energy_supply_results in results.items():
        for result_name in energy_supply_results.keys():
            # Create header row
            row_headers.append(energy_supply + ' ' + result_name)

    # Create results rows
    for t_idx in range(0, no_of_timesteps):
        row = []
        for energy_supply, energy_supply_results in results.items():
            for result_name, result_values in energy_supply_results.items():
                row.append(result_values[t_idx])
        rows_results.append(row)

    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(file_name, 'w', newline='') as postproc_file:
        writer = csv.writer(postproc_file)
        writer.writerow(row_headers)
        writer.writerows(rows_results)

def write_postproc_summary_file(file_path, total_emissions_rate, total_PE_rate, notional):
    if notional:
        emissions_rate_name = 'TER'
        pe_rate_name = 'TPER'
    else:
        emissions_rate_name = 'DER'
        pe_rate_name = 'DPER'

    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(file_path + 'postproc_summary.csv', 'w', newline='') as postproc_file:
        writer = csv.writer(postproc_file)
        writer.writerow(['','','Total'])
        writer.writerow([emissions_rate_name, 'kgCO2/m2', total_emissions_rate])
        writer.writerow([pe_rate_name,'kWh/m2',total_PE_rate])

def calc_TFA(project_dict):
     
    TFA = 0.0
    
    for zones in project_dict["Zone"].keys():
        TFA += project_dict["Zone"][zones]["area"]
        
    return TFA

def calc_nbeds(project_dict):
    if "NumberOfBedrooms" in project_dict:
        nbeds = int(project_dict["NumberOfBedrooms"])
    else:
        sys.exit("missing NumberOfBedrooms - required for FHS calculation")
    
    nbeds = min(nbeds,5)
    return nbeds

def calc_N_occupants(TFA, nbeds):
    
    if (TFA <= 0):
        # assume if floor area less than or equal to zero, TFA is not valid
        raise ValueError("Invalid floor area: {0}".format(TFA))
    
    # sigmoid curve is only used for one bedroom occupancy.
    # Therefore sigmoid parameters only listed if there is one bedroom
    sigmoid_params =   {1 :
                            {'j': 0.4373, 'k': -0.001902}
                        }
    
    # constant values are used to look up occupancy against the number of bedrooms
    TWO_BED_OCCUPANCY = 2.2472
    THREE_BED_OCCUPANCY = 2.9796
    FOUR_BED_OCCUPANCY = 3.3715
    FIVE_BED_OCCUPANCY = 3.8997
             
    if (nbeds == 1):
        N = 1 + sigmoid_params[nbeds]['j'] * (1 - math.exp(sigmoid_params[nbeds]['k'] * (TFA)**2))
    elif (nbeds == 2):
        N = TWO_BED_OCCUPANCY
    elif (nbeds == 3):
        N = THREE_BED_OCCUPANCY 
    elif (nbeds == 4):
        N = FOUR_BED_OCCUPANCY
    elif (nbeds >= 5):
        # 5 bedrooms or more are assumed to all have same occupancy
        N = FIVE_BED_OCCUPANCY
    else:
        # invalid number of bedrooms, raise ValueError exception
        raise ValueError("Invalid number of bedrooms: {0}".format(nbeds))
            
    return N

def create_occupancy(N_occupants):
    #in number of occupants
    occupancy_weekday_fhs = [
        1, 1, 1, 1, 1, 1, 0.5, 0.5, 0.5, 0.1, 0.1, 0.1, 0.1,
        0.2, 0.2, 0.2, 0.5, 0.5, 0.5, 0.8, 0.8, 1, 1, 1,
    ]
    occupancy_weekend_fhs = [
        1, 1, 1, 1, 1, 1, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8,
        0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 1, 1, 1
    ]
    
    schedule_occupancy_weekday = [
        x * N_occupants for x in occupancy_weekday_fhs
    ]
    schedule_occupancy_weekend = [
        x * N_occupants for x in occupancy_weekend_fhs
    ]
    
    return schedule_occupancy_weekday, schedule_occupancy_weekend

def create_metabolic_gains(project_dict, 
                           TFA, 
                           schedule_occupancy_weekday, 
                           schedule_occupancy_weekend):
    #Profile below is in Watts/m^2 body surface area, average adult has 1.8m^2 surface area
    # Nighttime metabolic rate based on figure for sleeping from CIBSE Guide A
    # Daytime metabolic rate based on figures for "seated quiet" from CIBSE Guide A
    body_area_average = 1.8
    night = 41.0
    daytm = 58.0
    metabolic_gains_fhs = [night] * 7 + [daytm] * 17
    #note divide by TFA. units are Wm^-2
    schedule_metabolic_gains_weekday = [
        occupancy * body_area_average * gains / TFA for occupancy, gains
        in zip(schedule_occupancy_weekday, metabolic_gains_fhs)
    ]
    schedule_metabolic_gains_weekend = [
        occupancy * body_area_average * gains / TFA for occupancy, gains
        in zip(schedule_occupancy_weekend, metabolic_gains_fhs)
    ]
    
    project_dict['InternalGains']['metabolic gains'] = {
        "start_day": 0,
        "time_series_step": 1,
        "schedule": {
            #watts m^-2
            "main": [{"repeat": 53, "value": "week"}],
            "week": [{"repeat": 5, "value": "weekday"},
                     {"repeat": 2, "value": "weekend"}],
            "weekday": schedule_metabolic_gains_weekday,
            "weekend": schedule_metabolic_gains_weekend

        }
    }

    return schedule_metabolic_gains_weekday, schedule_metabolic_gains_weekend

def create_heating_pattern(project_dict):
    '''
    space heating
    '''

    #07:00-09:30 and then 16:30-22:00
    heating_fhs_weekday = (
        [False for x in range(14)] +
        [True for x in range(5)] +
        [False for x in range(14)] +
        [True for x in range(11)] +
        [False for x in range(4)])
    # Start all-day HW schedule 1 hour before space heating
    hw_sched_allday_weekday \
        = ( [False for x in range(13)]
          + [True for x in range(31)]
          + [False for x in range(4)]
        )

    #07:00-09:30 and then 18:30-22:00
    heating_nonlivingarea_fhs_weekday = (
        [False for x in range(14)] +
        [True for x in range(5)] +
        [False for x in range(18)] +
        [True for x in range(7)] +
        [False for x in range(4)])

    #08:30 - 22:00
    heating_fhs_weekend = (
        [False for x in range(17)] +
        [True for x in range(27)] +
        [False for x in range(4)])
    # Start all-day HW schedule 1 hour before space heating
    hw_sched_allday_weekend \
        = ( [False for x in range(15)]
          + [True for x in range(29)]
          + [False for x in range(4)]
        )

    '''
    if there is not separate time control of the non-living rooms
    (i.e. control type 3 in SAP 10 terminology),
    the heating times are necessarily the same as the living room,
    so the evening heating period would also start at 16:30 on weekdays.
    '''
    controltype = 0
    if project_dict["HeatingControlType"]:
        if project_dict["HeatingControlType"] =="SeparateTimeAndTempControl":
            controltype = 3
        elif project_dict["HeatingControlType"] =="SeparateTempControl":
            controltype = 2
        else:
            sys.exit("invalid HeatingControlType (SeparateTempControl or SeparateTimeAndTempControl)")
    else:
        sys.exit("missing HeatingControlType (SeparateTempControl or SeparateTimeAndTempControl)")
    
    
    for zone in project_dict['Zone']:
        if "SpaceHeatControl" in project_dict["Zone"][zone].keys():
            if project_dict['Zone'][zone]["SpaceHeatControl"] == "livingroom":
                project_dict['Zone'][zone]['temp_setpnt_init'] = livingroom_setpoint_fhs

                project_dict['Control']['HeatingPattern_LivingRoom'] = {
                    "type": "SetpointTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule": {
                        "main": [{"repeat": 53, "value": "week"}],
                        "week": [{"repeat": 5, "value": "weekday"},
                                 {"repeat": 2, "value": "weekend"}],
                        "weekday": [livingroom_setpoint_fhs if x
                                    else None
                                    for x in heating_fhs_weekday],
                        "weekend": [livingroom_setpoint_fhs if x
                                    else None
                                    for x in heating_fhs_weekend],
                    }
                }
                if "SpaceHeatSystem" in project_dict["Zone"][zone].keys():
                    spaceheatsystem = project_dict["Zone"][zone]["SpaceHeatSystem"]
                    project_dict["SpaceHeatSystem"][spaceheatsystem]["Control"] = "HeatingPattern_LivingRoom"
                    if 'temp_setback' in project_dict["SpaceHeatSystem"][spaceheatsystem].keys():
                        project_dict['Control']['HeatingPattern_LivingRoom']['setpoint_min'] \
                            = project_dict["SpaceHeatSystem"][spaceheatsystem]['temp_setback']
                    if 'advanced_start' in project_dict["SpaceHeatSystem"][spaceheatsystem].keys():
                        project_dict['Control']['HeatingPattern_LivingRoom']['advanced_start'] \
                            = project_dict["SpaceHeatSystem"][spaceheatsystem]['advanced_start']
            
            elif project_dict['Zone'][zone]["SpaceHeatControl"] == "restofdwelling" \
            and controltype == 2:
                project_dict['Zone'][zone]['temp_setpnt_init'] = restofdwelling_setpoint_fhs

                project_dict['Control']['HeatingPattern_RestOfDwelling'] =  {
                    "type": "SetpointTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule":{
                        "main": [{"repeat": 53, "value": "week"}],
                        "week": [{"repeat": 5, "value": "weekday"},
                                 {"repeat": 2, "value": "weekend"}],
                        "weekday": [restofdwelling_setpoint_fhs if x
                                    else None
                                    for x in heating_fhs_weekday],
                        "weekend": [restofdwelling_setpoint_fhs if x
                                    else None
                                    for x in heating_fhs_weekend],
                    }
                }
                if "SpaceHeatSystem" in project_dict["Zone"][zone].keys():
                    spaceheatsystem = project_dict["Zone"][zone]["SpaceHeatSystem"]
                    project_dict["SpaceHeatSystem"][spaceheatsystem]["Control"] = "HeatingPattern_RestOfDwelling"
                    if 'temp_setback' in project_dict["SpaceHeatSystem"][spaceheatsystem].keys():
                        project_dict['Control']['HeatingPattern_RestOfDwelling']['setpoint_min'] \
                            = project_dict["SpaceHeatSystem"][spaceheatsystem]['temp_setback']
                    if 'advanced_start' in project_dict["SpaceHeatSystem"][spaceheatsystem].keys():
                        project_dict['Control']['HeatingPattern_RestOfDwelling']['advanced_start'] \
                            = project_dict["SpaceHeatSystem"][spaceheatsystem]['advanced_start']
            
            elif project_dict['Zone'][zone]["SpaceHeatControl"] == "restofdwelling" \
            and controltype == 3:
                project_dict['Zone'][zone]['temp_setpnt_init'] = restofdwelling_setpoint_fhs

                project_dict['Control']['HeatingPattern_RestOfDwelling'] =  {
                    "type": "SetpointTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule":{
                        "main": [{"repeat": 53, "value": "week"}],
                        "week": [{"repeat": 5, "value": "weekday"},
                                 {"repeat": 2, "value": "weekend"}],
                        "weekday": [restofdwelling_setpoint_fhs if x
                                    else None
                                    for x in heating_nonlivingarea_fhs_weekday],
                        "weekend": [restofdwelling_setpoint_fhs if x
                                    else None
                                    for x in heating_fhs_weekend],
                    }
                }
                if "SpaceHeatSystem" in project_dict["Zone"][zone].keys():
                    spaceheatsystem = project_dict["Zone"][zone]["SpaceHeatSystem"]
                    project_dict["SpaceHeatSystem"][spaceheatsystem]["Control"] = "HeatingPattern_RestOfDwelling"
                    if 'temp_setback' in project_dict["SpaceHeatSystem"][spaceheatsystem].keys():
                        project_dict['Control']['HeatingPattern_RestOfDwelling']['setpoint_min'] \
                            = project_dict["SpaceHeatSystem"][spaceheatsystem]['temp_setback']
                    if 'advanced_start' in project_dict["SpaceHeatSystem"][spaceheatsystem].keys():
                        project_dict['Control']['HeatingPattern_RestOfDwelling']['advanced_start'] \
                            = project_dict["SpaceHeatSystem"][spaceheatsystem]['advanced_start']
        #todo: else condition to deal with zone that doesnt have specified livingroom/rest of dwelling

def create_water_heating_pattern(project_dict):
    '''
    water heating pattern - if system is not instantaneous, hold at setpoint
    00:00-07:00 and then reheat as necessary 24/7
    '''
    project_dict['Control'][hw_timer_main_name] = {
        "type": "OnOffTimeControl",
        "start_day": 0,
        "time_series_step": 0.5,
        "schedule": {
            "main": [{"value": "day", "repeat": 365}],
            "day": [{"value": True, "repeat": 48}]
        }
    }
    project_dict['Control'][hw_timer_hold_at_setpnt_name] = {
        "type": "OnOffTimeControl",
        "start_day": 0,
        "time_series_step": 0.5,
        "schedule": {
            "main": [{"value": "day", "repeat": 365}],
            "day": [
                {"value": True, "repeat": 14},
                {"value": False, "repeat": 34}
            ]
        }
    }

    for hwsource in project_dict['HotWaterSource']:
        hw_source_type = project_dict['HotWaterSource'][hwsource]["type"]
        if hw_source_type == "StorageTank":
            project_dict['HotWaterSource'][hwsource]['Control_hold_at_setpnt'] \
                = hw_timer_hold_at_setpnt_name
            for heatsource in project_dict['HotWaterSource'][hwsource]["HeatSource"]:
                project_dict['HotWaterSource'][hwsource]["HeatSource"][heatsource]["Control"] \
                    = hw_timer_main_name

        elif hw_source_type in ("CombiBoiler", "PointOfUse", "HIU"):
            # Instantaneous water heating systems must be available 24 hours a day
            pass
        else:
            sys.exit("Standard water heating schedule not defined for HotWaterSource type"
                      + hw_source_type)

def create_evaporative_losses(project_dict,TFA, N_occupants):
    evaporative_losses_fhs = -40 * N_occupants / TFA
    
    project_dict['InternalGains']['EvaporativeLosses'] = {
        "start_day": 0,
        "time_series_step": 1,
        "schedule": {
            #in Wm^-2
            "main": [{"value": evaporative_losses_fhs, "repeat": 8760 }]
        }
    } #repeats for length of simulation which in FHS should be whole year.

def create_lighting_gains(project_dict, TFA, N_occupants):
    '''
    Calculate the annual energy requirement in kWh using the procedure described in SAP 10.2 up to and including step 9.
    Divide this by 365 to get the average daily energy use.
    Multiply the daily energy consumption figure by the following profiles to
    create a daily profile for each month of the year (to be applied to all days in that month).
    '''

    '''
    here we calculate an overall lighting efficacy as
    the average of zone lighting efficacies weighted by zone
    floor area.
    '''
    lighting_efficacy = 0
    for zone in project_dict["Zone"]:
        if "Lighting"  not in project_dict["Zone"][zone].keys():
            sys.exit("missing lighting in zone "+ zone)
        if "efficacy" not in project_dict["Zone"][zone]["Lighting"].keys():
            sys.exit("missing lighting efficacy in zone "+ zone)
        lighting_efficacy += project_dict["Zone"][zone]["Lighting"]["efficacy"] * project_dict["Zone"][zone]["area"] / TFA
        
    if lighting_efficacy == 0:
        sys.exit('invalid/missing lighting efficacy for all zones')
        
    
    # TODO Consider defining large tables like this in a separate file rather than inline
    avg_monthly_halfhr_profiles = [
        [0.029235831, 0.02170637, 0.016683155, 0.013732757, 0.011874713, 0.010023118, 0.008837131, 0.007993816,
         0.007544302, 0.007057335, 0.007305208, 0.007595198, 0.009170401, 0.013592425, 0.024221707, 0.034538234,
         0.035759809, 0.02561524, 0.019538678, 0.017856399, 0.016146846, 0.014341097, 0.013408345, 0.013240894,
         0.013252628, 0.013314013, 0.013417126, 0.01429735, 0.014254224, 0.014902582, 0.017289786, 0.023494947,
         0.035462982, 0.050550653, 0.065124006, 0.072629223, 0.073631053, 0.074451912, 0.074003097, 0.073190397,
         0.071169797, 0.069983033, 0.06890179, 0.066130187, 0.062654436, 0.056634675, 0.047539646, 0.037801233],
        [0.026270349, 0.01864863, 0.014605535, 0.01133541, 0.009557625, 0.008620514, 0.007385915, 0.00674999,
         0.006144089, 0.005812534, 0.005834644, 0.006389013, 0.007680219, 0.013106226, 0.021999709, 0.027144574,
         0.02507541, 0.0179487, 0.014855879, 0.012930469, 0.011690622, 0.010230198, 0.00994897, 0.009668602,
         0.00969183, 0.010174279, 0.011264866, 0.011500069, 0.011588248, 0.011285427, 0.012248949, 0.014420402,
         0.01932017, 0.027098032, 0.044955369, 0.062118024, 0.072183735, 0.075100799, 0.075170654, 0.072433133,
         0.070588417, 0.069756433, 0.068356831, 0.06656098, 0.06324827, 0.055573729, 0.045490296, 0.035742204],
        [0.02538112, 0.018177936, 0.012838313, 0.00961673, 0.007914015, 0.006844738, 0.00611386, 0.005458354,
         0.00508359, 0.004864933, 0.004817922, 0.005375289, 0.006804643, 0.009702514, 0.013148583, 0.013569968,
         0.01293754, 0.009183378, 0.007893734, 0.00666975, 0.006673791, 0.006235776, 0.006096299, 0.006250229,
         0.006018285, 0.00670324, 0.006705105, 0.006701531, 0.006893458, 0.006440525, 0.006447363, 0.007359989,
         0.009510975, 0.011406472, 0.017428875, 0.026635564, 0.042951415, 0.057993474, 0.066065305, 0.067668248,
         0.067593187, 0.067506237, 0.065543759, 0.063020652, 0.06004127, 0.052838397, 0.043077683, 0.033689246],
        [0.029044978, 0.020558675, 0.014440871, 0.010798435, 0.008612364, 0.007330799, 0.006848797, 0.006406058,
         0.00602619, 0.005718987, 0.005804901, 0.006746423, 0.007160898, 0.008643678, 0.010489867, 0.011675722,
         0.011633729, 0.008939881, 0.007346857, 0.007177037, 0.007113926, 0.007536109, 0.007443049, 0.006922747,
         0.00685514, 0.006721853, 0.006695838, 0.005746367, 0.005945173, 0.005250153, 0.005665752, 0.006481695,
         0.006585193, 0.00751989, 0.009038481, 0.009984259, 0.011695555, 0.014495872, 0.018177089, 0.027110627,
         0.042244993, 0.056861545, 0.064008071, 0.062680016, 0.060886258, 0.055751568, 0.048310205, 0.038721632],
        [0.023835444, 0.016876637, 0.012178456, 0.009349274, 0.007659691, 0.006332517, 0.005611274, 0.005650048,
         0.005502101, 0.005168442, 0.005128425, 0.005395259, 0.004998272, 0.005229362, 0.006775116, 0.007912694,
         0.008514274, 0.006961449, 0.00630672, 0.00620858, 0.005797218, 0.005397357, 0.006006318, 0.005593869,
         0.005241095, 0.005212189, 0.00515531, 0.004906504, 0.004757624, 0.004722969, 0.004975738, 0.005211879,
         0.005684004, 0.006331507, 0.007031149, 0.008034144, 0.008731998, 0.010738922, 0.013170262, 0.016638631,
         0.021708313, 0.0303703, 0.043713685, 0.051876584, 0.054591464, 0.05074126, 0.043109775, 0.033925231],
        [0.023960632, 0.016910619, 0.012253193, 0.009539031, 0.007685214, 0.006311553, 0.00556675, 0.005140391,
         0.004604673, 0.004352551, 0.004156956, 0.004098101, 0.00388452, 0.00433039, 0.005658606, 0.006828804,
         0.007253075, 0.005872749, 0.004923197, 0.004521087, 0.004454765, 0.004304616, 0.004466648, 0.004178716,
         0.004186183, 0.003934784, 0.004014114, 0.003773073, 0.003469885, 0.003708517, 0.003801095, 0.004367245,
         0.004558263, 0.005596378, 0.005862632, 0.006068665, 0.006445161, 0.007402661, 0.007880006, 0.009723385,
         0.012243076, 0.016280074, 0.023909324, 0.03586776, 0.046595858, 0.047521241, 0.041417407, 0.03322265],
        [0.024387138, 0.017950032, 0.01339296, 0.010486231, 0.008634325, 0.00752814, 0.006562675, 0.006180296,
         0.00566116, 0.005092682, 0.004741384, 0.004680853, 0.00479228, 0.004921812, 0.005950605, 0.007010479,
         0.007057257, 0.005651136, 0.004813649, 0.00454666, 0.004121156, 0.003793481, 0.004122788, 0.004107635,
         0.004363668, 0.004310674, 0.004122943, 0.004014391, 0.004009496, 0.003805058, 0.004133355, 0.004188447,
         0.005268291, 0.005964825, 0.005774607, 0.006292344, 0.006813734, 0.007634982, 0.008723529, 0.009855823,
         0.012318322, 0.017097237, 0.026780014, 0.037823534, 0.046797578, 0.045940354, 0.039472789, 0.033058217],
        [0.023920296, 0.01690733, 0.012917415, 0.010191735, 0.008787867, 0.007681138, 0.006600128, 0.006043227,
         0.005963814, 0.005885256, 0.006164212, 0.005876554, 0.005432168, 0.00580157, 0.00641092, 0.007280576,
         0.00811752, 0.007006283, 0.006505718, 0.005917892, 0.005420978, 0.005527121, 0.005317478, 0.004793601,
         0.004577663, 0.004958332, 0.005159584, 0.004925386, 0.005192686, 0.0054453, 0.005400465, 0.005331386,
         0.005994507, 0.006370203, 0.006800758, 0.007947816, 0.009005592, 0.010608225, 0.012905449, 0.015976909,
         0.024610768, 0.036414926, 0.04680022, 0.050678553, 0.051188831, 0.046725936, 0.03998602, 0.032496965],
        [0.022221313, 0.016428778, 0.01266253, 0.010569518, 0.008926713, 0.007929788, 0.007134802, 0.006773883,
         0.006485147, 0.006766094, 0.007202971, 0.007480145, 0.008460127, 0.011414527, 0.014342431, 0.01448993,
         0.012040415, 0.008520428, 0.0077578, 0.006421555, 0.005889369, 0.005915144, 0.006229011, 0.005425193,
         0.005094464, 0.005674584, 0.005898523, 0.006504338, 0.005893063, 0.005967896, 0.0061056, 0.006017598,
         0.007500459, 0.008041236, 0.0099079, 0.012297435, 0.01592606, 0.021574549, 0.032780393, 0.04502082,
         0.054970312, 0.05930568, 0.060189471, 0.057269758, 0.05486585, 0.047401041, 0.038520417, 0.029925316],
        [0.023567522, 0.016304584, 0.012443113, 0.009961033, 0.008395854, 0.007242191, 0.006314956, 0.005722235,
         0.005385313, 0.005197814, 0.005444756, 0.0064894, 0.008409762, 0.015347201, 0.025458901, 0.028619409,
         0.023359044, 0.014869014, 0.011900433, 0.010931316, 0.010085903, 0.009253621, 0.008044246, 0.007866149,
         0.007665985, 0.007218414, 0.00797338, 0.008005782, 0.007407311, 0.008118996, 0.008648934, 0.010378068,
         0.013347814, 0.018541666, 0.026917161, 0.035860046, 0.049702909, 0.063560224, 0.069741764, 0.070609245,
         0.069689625, 0.069439031, 0.068785313, 0.065634051, 0.062207874, 0.053986076, 0.043508937, 0.033498873],
        [0.025283869, 0.018061868, 0.013832406, 0.01099122, 0.009057752, 0.007415348, 0.006415533, 0.006118688,
         0.005617255, 0.005084989, 0.005552217, 0.006364787, 0.00792208, 0.014440148, 0.02451, 0.02993728,
         0.024790064, 0.016859553, 0.013140437, 0.012181571, 0.010857371, 0.010621789, 0.010389982, 0.010087677,
         0.00981219, 0.0097001, 0.01014589, 0.01052881, 0.01044948, 0.011167223, 0.013610154, 0.02047533,
         0.035335895, 0.05409712, 0.067805633, 0.074003571, 0.077948793, 0.078981046, 0.077543712, 0.074620225,
         0.072631194, 0.070886175, 0.06972224, 0.068354439, 0.063806373, 0.055709895, 0.045866391, 0.035248054],
        [0.030992394, 0.022532047, 0.016965296, 0.013268634, 0.010662773, 0.008986943, 0.007580978, 0.006707669,
         0.00646337, 0.006180296, 0.006229094, 0.006626391, 0.00780049, 0.013149437, 0.022621172, 0.033064744,
         0.035953213, 0.029010413, 0.023490829, 0.020477646, 0.018671663, 0.017186751, 0.016526661, 0.015415424,
         0.014552683, 0.014347935, 0.014115058, 0.013739051, 0.014944386, 0.017543021, 0.021605977, 0.032100988,
         0.049851633, 0.063453382, 0.072579104, 0.076921792, 0.079601317, 0.079548711, 0.078653413, 0.076225647,
         0.073936893, 0.073585752, 0.071911165, 0.069220452, 0.065925982, 0.059952377, 0.0510938, 0.041481111]]

    #from analysis of EFUS 2017 data
    lumens = 1418 * (TFA * N_occupants) ** 0.41

    #dropped 1/3 - 2/3 split based on SAP2012 assumptions about portable lighting
    kWhperyear = lumens/lighting_efficacy
    kWhperday = kWhperyear / 365

    lighting_gains_W = []
        
    for monthly_profile in avg_monthly_halfhr_profiles:

        '''
        To obtain the lighting gains,
        the above should be converted to Watts by multiplying the individual half-hourly figure by (2 x 1000).
        Since some lighting energy will be used in external light
        (e.g. outdoor security lights or lights in unheated spaces like garages and sheds)
        a factor of 0.85 is also applied to get the internal gains from lighting.
        '''
        lighting_gains_W.append([(frac * kWhperday) * 2 * 1000 for frac in monthly_profile])
    
    project_dict['ApplianceGains']['lighting'] = {
        "type": "lighting",
        "start_day": 0,
        "time_series_step" : 0.5,
        "gains_fraction": 0.85,
        "EnergySupply": energysupplyname_electricity,
        "schedule": {
            "main": [{"value": "jan", "repeat": 31},
                    {"value": "feb", "repeat": 28},
                    {"value": "mar", "repeat": 31},
                    {"value": "apr", "repeat": 30},
                    {"value": "may", "repeat": 31},
                    {"value": "jun", "repeat": 30},
                    {"value": "jul", "repeat": 31},
                    {"value": "aug", "repeat": 31},
                    {"value": "sep", "repeat": 30},
                    {"value": "oct", "repeat": 31},
                    {"value": "nov", "repeat": 30},
                    {"value": "dec", "repeat": 31}
                     ],
            "jan":lighting_gains_W[0],
            "feb":lighting_gains_W[1],
            "mar":lighting_gains_W[2],
            "apr":lighting_gains_W[3],
            "may":lighting_gains_W[4],
            "jun":lighting_gains_W[5],
            "jul":lighting_gains_W[6],
            "aug":lighting_gains_W[7],
            "sep":lighting_gains_W[8],
            "oct":lighting_gains_W[9],
            "nov":lighting_gains_W[10],
            "dec":lighting_gains_W[11]
        }
    }


def create_cooking_gains(project_dict,TFA, N_occupants):
    
    cooking_profile_fhs = [
        0.001192419, 0.000825857, 0.000737298, 0.000569196,
        0.000574409, 0.000573778, 0.000578369, 0.000574619, 0.000678235,
        0.000540799, 0.000718043, 0.002631192, 0.002439288, 0.003263445,
        0.003600656, 0.005743044, 0.011250675, 0.015107564, 0.014475307,
        0.016807917, 0.018698336, 0.018887283, 0.021856976, 0.047785397,
        0.08045051, 0.099929701, 0.042473353, 0.02361216, 0.015650513,
        0.014345379, 0.015951211, 0.01692045, 0.037738026, 0.066195428,
        0.062153502, 0.073415686, 0.077486476, 0.069093846, 0.046706527,
        0.024924648, 0.014783978, 0.009192004, 0.005617715, 0.0049381,
        0.003529689, 0.002365773, 0.001275927, 0.001139293
    ]
    
    EC1elec = 0
    EC1gas = 0
    EC2elec = 0
    EC2gas = 0
    '''
    check for gas and/or electric cooking. Remove any existing objects
    so that we can add our own (just one for gas and one for elec)
    '''
    cookingenergysupplies = []
    for item in list(project_dict["ApplianceGains"]):
        if project_dict["ApplianceGains"][item]["type"]=="cooking":
            cookingenergysupplies.append(project_dict["ApplianceGains"][item]["EnergySupply"])
            project_dict["ApplianceGains"].pop(item)

    #From the cooking energy supplies, need to find the associated fuel they use
    cookingfuels=[]
    for item in cookingenergysupplies:
        fuel_type = project_dict["EnergySupply"][item]["fuel"]
        cookingfuels.append(fuel_type)

    if "electricity" in cookingfuels and "mains_gas" in cookingfuels:
        EC1elec = 86
        EC2elec = 49
        EC1gas = 150
        EC2gas = 86
    elif "mains_gas" in cookingfuels:
        EC1elec = 0
        EC2elec = 0
        EC1gas = 299
        EC2gas = 171
    elif "electricity" in cookingfuels:
        EC1elec = 171
        EC2elec = 98
        EC1gas = 0
        EC2gas = 0
        #TODO - if there is cooking with energy supply other than
        #mains gas or electric, it could be accounted for here -
        #but presently it will be ignored.
        
    annual_cooking_elec_kWh = EC1elec + EC2elec * N_occupants
    annual_cooking_gas_kWh = EC1gas + EC2gas * N_occupants
    
    #energy consumption, W_m2, gains factor not applied
    cooking_elec_profile_W = [(1000 * 2) * annual_cooking_elec_kWh / 365
                              * halfhr for halfhr in cooking_profile_fhs]
    cooking_gas_profile_W = [(1000 * 2) * annual_cooking_gas_kWh / 365
                             * halfhr for halfhr in cooking_profile_fhs]

    
    #add back gas and electric cooking gains if they are present 
    if "mains_gas" in cookingfuels:
        project_dict['ApplianceGains'][gas_cook_obj_name] = {
            "type":"cooking",
            "EnergySupply": "mains gas",
            "start_day" : 0,
            "time_series_step": 0.5,
            "gains_fraction": 0.5, 
            "schedule": {
                "main": [{"repeat": 365, "value": "day"}],
                "day": cooking_gas_profile_W
            }
        }
    if "electricity" in cookingfuels:
        project_dict['ApplianceGains'][elec_cook_obj_name] = {
            "type":"cooking",
            "EnergySupply": energysupplyname_electricity,
            "start_day" : 0,
            "time_series_step": 0.5,
            "gains_fraction": 0.5,
            "schedule": {
                "main": [{"repeat": 365, "value": "day"}],
                "day": cooking_elec_profile_W
            }
        }

def create_appliance_gains(project_dict,TFA,N_occupants):
    
    avg_monthly_hr_profiles = [
        [0.025995114, 0.023395603, 0.022095847, 0.020796091, 0.019496336, 0.022095847, 0.02729487, 0.040292427, 0.048090962, 0.049390717, 0.050690473, 0.049390717, 0.053289984, 0.049390717, 0.050690473, 0.053289984, 0.074086076, 0.087083633, 0.08188461, 0.070186809, 0.064987786, 0.057189252, 0.046791206, 0.033793649],
        [0.025995114, 0.023395603, 0.022095847, 0.020796091, 0.019496336, 0.022095847, 0.02729487, 0.032493893, 0.046791206, 0.051990229, 0.049390717, 0.046791206, 0.048090962, 0.046791206, 0.04549145, 0.049390717, 0.062388274, 0.074086076, 0.080584854, 0.067587297, 0.059788763, 0.050690473, 0.044191694, 0.032493893],
        [0.024695359, 0.020796091, 0.020796091, 0.019496336, 0.020796091, 0.022095847, 0.029894381, 0.041592183, 0.04549145, 0.048090962, 0.04549145, 0.04549145, 0.049390717, 0.048090962, 0.048090962, 0.049390717, 0.057189252, 0.070186809, 0.07278632, 0.067587297, 0.061088519, 0.051990229, 0.041592183, 0.029894381],
        [0.022095847, 0.022095847, 0.022095847, 0.022095847, 0.023395603, 0.029894381, 0.038992672, 0.046791206, 0.046791206, 0.044191694, 0.046791206, 0.048090962, 0.044191694, 0.042891939, 0.044191694, 0.051990229, 0.062388274, 0.061088519, 0.058489007, 0.057189252, 0.050690473, 0.041592183, 0.033793649, 0.024695359],
        [0.024695359, 0.022095847, 0.020796091, 0.020796091, 0.023395603, 0.031194137, 0.038992672, 0.044191694, 0.048090962, 0.046791206, 0.044191694, 0.04549145, 0.041592183, 0.037692916, 0.038992672, 0.049390717, 0.05458974, 0.058489007, 0.051990229, 0.055889496, 0.050690473, 0.041592183, 0.031194137, 0.024695359],
        [0.022095847, 0.020796091, 0.020796091, 0.019496336, 0.020796091, 0.024695359, 0.032493893, 0.042891939, 0.044191694, 0.041592183, 0.040292427, 0.042891939, 0.040292427, 0.038992672, 0.040292427, 0.044191694, 0.053289984, 0.057189252, 0.048090962, 0.048090962, 0.04549145, 0.041592183, 0.031194137, 0.024695359],
        [0.022095847, 0.020796091, 0.020796091, 0.019496336, 0.020796091, 0.024695359, 0.032493893, 0.041592183, 0.042891939, 0.042891939, 0.041592183, 0.041592183, 0.040292427, 0.037692916, 0.037692916, 0.044191694, 0.051990229, 0.05458974, 0.046791206, 0.046791206, 0.04549145, 0.042891939, 0.031194137, 0.024695359],
        [0.022095847, 0.020796091, 0.020796091, 0.019496336, 0.020796091, 0.024695359, 0.032493893, 0.044191694, 0.044191694, 0.044191694, 0.044191694, 0.044191694, 0.042891939, 0.040292427, 0.041592183, 0.044191694, 0.051990229, 0.055889496, 0.050690473, 0.051990229, 0.049390717, 0.042891939, 0.031194137, 0.024695359],
        [0.022095847, 0.020796091, 0.020796091, 0.019496336, 0.023395603, 0.029894381, 0.040292427, 0.041592183, 0.044191694, 0.044191694, 0.04549145, 0.044191694, 0.042891939, 0.042891939, 0.042891939, 0.051990229, 0.059788763, 0.064987786, 0.061088519, 0.058489007, 0.051990229, 0.038992672, 0.031194137, 0.023395603],
        [0.022095847, 0.020796091, 0.019496336, 0.022095847, 0.023395603, 0.029894381, 0.040292427, 0.046791206, 0.049390717, 0.04549145, 0.046791206, 0.049390717, 0.04549145, 0.044191694, 0.04549145, 0.053289984, 0.067587297, 0.07278632, 0.066287542, 0.059788763, 0.053289984, 0.042891939, 0.031194137, 0.023395603],
        [0.024695359, 0.022095847, 0.020796091, 0.020796091, 0.020796091, 0.024695359, 0.029894381, 0.042891939, 0.048090962, 0.049390717, 0.04549145, 0.04549145, 0.046791206, 0.046791206, 0.044191694, 0.051990229, 0.064987786, 0.08188461, 0.076685587, 0.067587297, 0.061088519, 0.05458974, 0.04549145, 0.032493893],
        [0.025995114, 0.023395603, 0.022095847, 0.020796091, 0.019496336, 0.022095847, 0.02729487, 0.032493893, 0.048090962, 0.053289984, 0.051990229, 0.05458974, 0.057189252, 0.051990229, 0.055889496, 0.058489007, 0.075385832, 0.083184366, 0.08188461, 0.068887053, 0.062388274, 0.055889496, 0.046791206, 0.033793649]]
    #old relation based on sap2012, efus 1998 data verified in 2013
    #EA_annual_kWh = 207.8 * (TFA * N_occupants) ** 0.4714
    
    #new relation based on analysis of EFUS 2017 monitoring data
    EA_annual_kWh = 145 * (TFA * N_occupants) ** 0.49
    
    appliance_gains_W = []
    for monthly_profile in avg_monthly_hr_profiles:
        appliance_gains_W.append([1000 * EA_annual_kWh * frac / 365
                                  for frac in monthly_profile])
        
    project_dict['ApplianceGains'][appl_obj_name] = {
        "type": "appliances",
        "EnergySupply": energysupplyname_electricity,
        "start_day": 0,
        "time_series_step": 1,
        # Internal gains are reduced from washer/dryers and dishwasher waste heat losses. 
        # Assume 70% of their heat is lost as waste heat in waste water or vented hot air, 
        # or 30% of total appliance energy, leaving 70% appliance gains fraction
        "gains_fraction": 0.7,
        "schedule": {
            #watts
            "main": [{"value": "jan", "repeat": 31},
                    {"value": "feb", "repeat": 28},
                    {"value": "mar", "repeat": 31},
                    {"value": "apr", "repeat": 30},
                    {"value": "may", "repeat": 31},
                    {"value": "jun", "repeat": 30},
                    {"value": "jul", "repeat": 31},
                    {"value": "aug", "repeat": 31},
                    {"value": "sep", "repeat": 30},
                    {"value": "oct", "repeat": 31},
                    {"value": "nov", "repeat": 30},
                    {"value": "dec", "repeat": 31}
                     ],
            "jan": appliance_gains_W[0],
            "feb": appliance_gains_W[1],
            "mar": appliance_gains_W[2],
            "apr": appliance_gains_W[3],
            "may": appliance_gains_W[4],
            "jun": appliance_gains_W[5],
            "jul": appliance_gains_W[6],
            "aug": appliance_gains_W[7],
            "sep": appliance_gains_W[8],
            "oct": appliance_gains_W[9],
            "nov": appliance_gains_W[10],
            "dec": appliance_gains_W[11]
        }
    }
    
# check whether the shower flowrate is not less than the minimum allowed    
def check_shower_flowrate(project_dict):
    
    MIN_FLOWRATE = 8.0 # minimum flow allowed. Return False if below minimum.
    showers = project_dict['Shower']
  
    for name, shower in showers.items():
        if 'flowrate' in shower:
            flowrate = shower['flowrate']
            if flowrate < MIN_FLOWRATE:
                print("Invalid flow rate: {0} l/s in shower with name {1}".format(flowrate, name), 
                      file=sys.stderr)
                return False
    return True   
        
def create_hot_water_use_pattern(project_dict, TFA, N_occupants, cold_water_feed_temps):
    
    if not (check_shower_flowrate(project_dict)):
        sys.exit("Exited: invalid flow rate")    
    
    #temperature of mixed hot water for event
    event_temperature = 41.0
    HW_temperature = 52.0
    mean_feedtemp = sum(cold_water_feed_temps) / len(cold_water_feed_temps)
    mean_delta_T = HW_temperature - mean_feedtemp
    
    annual_HW_events = []
    annual_HW_events_energy = []
    startmod = 0 #this changes which day of the week we start on. 0 is monday.

    #SAP 2012 relation
    #vol_daily_average = (25 * N_occupants) + 36
    
    #new relation based on Boiler Manufacturer data and EST surveys
    #reduced by 15% to account for pipework losses present in the source data
    vol_HW_daily_average =  0.85 * 60.3 * N_occupants ** 0.71
    
    HWeventgen = HW_events_generator(vol_HW_daily_average)
    ref_eventlist = HWeventgen.build_annual_HW_events(startmod)
    ref_HW_vol = 0
    for event in ref_eventlist:  
        '''
        NB while calibration is done by event volumes we use the event durations from the HW csv data for showers
        so the actual hw use predicted by sap depends on shower flowrates in dwelling, but this value does not
        '''
        ref_HW_vol += float(event["vol"])
    # Add daily average hot water use to hot water only heat pump (HWOHP) object, if present
    # TODO This is probably only valid if HWOHP is the only heat source for the
    #      storage tank. Make this more robust/flexible in future.
    for hw_source_obj in project_dict['HotWaterSource'].values():
        if hw_source_obj['type'] == 'StorageTank':
            for heat_source_obj in hw_source_obj['HeatSource'].values():
                if heat_source_obj['type'] == 'HeatPump_HWOnly':
                    heat_source_obj['vol_hw_daily_average'] = vol_HW_daily_average

    FHW = (365 * vol_HW_daily_average) / ref_HW_vol



    '''
    if part G has been complied with, apply 5% reduction to duration of Other events
    '''
    partGbonus = 1.0
    if "PartGcompliance" in project_dict:
        if project_dict["PartGcompliance"] == True:
            partGbonus = 0.95
            #adjusting the size of the bath here as bath duration is not utilised by engine,
            #only bath size
    else:
        sys.exit("Part G compliance missing from input file")
    
    HW_event_aa = HW_event_adjust_allocate(project_dict,
                     FHW,
                     event_temperature, 
                     HW_temperature, 
                     cold_water_feed_temps,
                     partGbonus
                     )
    
    '''
    now create lists of events
    Shower events should be  evenly spread across all showers in dwelling
    and so on for baths etc.
    '''
    hrlyevents = [[] for x in range(8760)]
    for i, event in enumerate(ref_eventlist):
        if event["type"] != "None":
            if event["type"].find("shower")!=-1:
                eventtype, name, durationfunc = HW_event_aa.get_shower()
            elif event["type"].find("bath")!=-1:
                eventtype, name, durationfunc = HW_event_aa.get_bath()
            else:
                eventtype, name, durationfunc = HW_event_aa.get_other()
            
            eventstart = event["time"]
            duration = durationfunc(event)
                
            if not (name in project_dict["Shower"] and project_dict["Shower"][name]["type"] == "InstantElecShower"):
                #IES can overlap with anything so ignore them entirely
                #TODO - implies 2 uses of the same IES may overlap, could check them separately
                HWeventgen.overlap_check(hrlyevents, ["Shower", "Bath"], eventstart, duration)
                hrlyevents[math.floor(eventstart)].append({"type":"Shower",
                                                           "eventstart": eventstart,
                                                           "eventend": eventstart + duration / 60.0})
                
            project_dict["Events"][eventtype][name].append(
                {"start": eventstart,
                "duration": duration, 
                "temperature": event_temperature}
                )

def create_window_opening_schedule(project_dict):

    if "Window_Opening_For_Cooling" not in project_dict.keys():
        print("Warning: No window opening for cooling has been specified. The "
              "calculation will assume that there are no openable windows.")
        return

    window_opening_setpoint = 22.0

    # 09:00-22:00
    project_dict['Control']['WindowOpening_LivingRoom'] = {
        "type": "SetpointTimeControl",
        "start_day" : 0,
        "time_series_step": 0.5,
        "schedule": {
            "main": [{"repeat": 365, "value": "day"}],
            "day": [
                {"repeat": 18, "value": None},
                {"repeat": 26, "value": window_opening_setpoint},
                {"repeat": 4, "value": None},
            ],
        }
    }

    # 08:00-23:00
    project_dict['Control']['WindowOpening_RestOfDwelling'] = {
        "type": "SetpointTimeControl",
        "start_day" : 0,
        "time_series_step": 0.5,
        "schedule": {
            "main": [{"repeat": 365, "value": "day"}],
            "day": [
                {"repeat": 16, "value": None},
                {"repeat": 30, "value": window_opening_setpoint},
                {"repeat": 2, "value": None},
            ],
        }
    }

    for z_name in project_dict['Zone'].keys():
        if project_dict['Zone'][z_name]["SpaceHeatControl"] == "livingroom":
            project_dict['Zone'][z_name]['Control_WindowOpening'] = 'WindowOpening_LivingRoom'
        elif project_dict['Zone'][z_name]["SpaceHeatControl"] == "restofdwelling":
            project_dict['Zone'][z_name]['Control_WindowOpening'] = 'WindowOpening_RestOfDwelling'
        else:
            sys.exit('SpaceHeatControl value for zone "' + z_name + '" not valid.')

def create_cooling(project_dict):
    cooling_setpoint = 24.0

    #07:00-09:30 and then 18:30-22:00
    cooling_subschedule_livingroom_weekday = (
        [None for x in range(14)] +
        [cooling_setpoint for x in range(5)] +
        [None for x in range(18)] +
        [cooling_setpoint for x in range(7)] +
        [None for x in range(4)])

    #08:30 - 22:30
    cooling_subschedule_livingroom_weekend = (
        [None for x in range(17)] +
        [cooling_setpoint for x in range(28)] +
        [None for x in range(3)])

    cooling_subschedule_restofdwelling = (
        #22:00-07:00 - ie nighttime only
        [cooling_setpoint for x in range(14)] +
        [None for x in range(30)] +
        [cooling_setpoint for x in range(4)]
    )
    
    for zone in project_dict['Zone']:
        if "SpaceHeatControl" in project_dict['Zone'][zone]:
            if project_dict['Zone'][zone]["SpaceHeatControl"] == "livingroom" and "SpaceCoolSystem" in project_dict['Zone'][zone]:
                project_dict['Control']['Cooling_LivingRoom'] = {
                    "type": "SetpointTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule": {
                        "main": [{"repeat": 53, "value": "week"}],
                        "week": [{"repeat": 5, "value": "weekday"},
                                 {"repeat": 2, "value": "weekend"}],
                        "weekday": cooling_subschedule_livingroom_weekday,
                        "weekend": cooling_subschedule_livingroom_weekend,
                    }
                }
                spacecoolsystem = project_dict["Zone"][zone]["SpaceCoolSystem"]
                project_dict["SpaceCoolSystem"][spacecoolsystem]["Control"] = "Cooling_LivingRoom"
                if 'temp_setback' in project_dict["SpaceCoolSystem"][spacecoolsystem].keys():
                    project_dict['Control']['Cooling_LivingRoom']['setpoint_max'] \
                        = project_dict["SpaceCoolSystem"][spacecoolsystem]['temp_setback']

            elif project_dict['Zone'][zone]["SpaceHeatControl"] == "restofdwelling" and "SpaceCoolSystem" in project_dict['Zone'][zone]:
                project_dict['Control']['Cooling_RestOfDwelling'] = {
                    "type": "SetpointTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule": {
                        "main": [{"repeat": 365, "value": "day"}],
                        "day": cooling_subschedule_restofdwelling
                    }
                }
        
                spacecoolsystem = project_dict["Zone"][zone]["SpaceCoolSystem"]
                project_dict["SpaceCoolSystem"][spacecoolsystem]["Control"] = "Cooling_RestOfDwelling"
                if 'temp_setback' in project_dict["SpaceCoolSystem"][spacecoolsystem].keys():
                    project_dict['Control']['Cooling_RestOfDwelling']['setpoint_max'] \
                        = project_dict["SpaceCoolSystem"][spacecoolsystem]['temp_setback']

def create_cold_water_feed_temps(project_dict):
    
    #24 hour average feed temperature (degreees Celsius) per month m. SAP 10.2 Table J1
    T24m_header_tank = [11.1, 11.3, 12.3, 14.5, 16.2, 18.8, 21.3, 19.3, 18.7, 16.2, 13.2, 11.2]
    T24m_mains = [8, 8.2, 9.3, 12.7, 14.6, 16.7, 18.4, 17.6, 16.6, 14.3, 11.1, 8.5]
    T24m=[]
    feedtype=""
    #typical fall in feed temp from midnight to 6am
    delta = 1.5
    
    if "header tank" in project_dict["ColdWaterSource"]:
        T24m = T24m_header_tank
        feedtype="header tank"
    else:
        T24m = T24m_mains
        feedtype="mains water"
    
    cold_feed_schedulem=[]
    
    for T in T24m:
        #typical cold feed temp between 3pm and midnight
        Teveningm = T + (delta * 15 /48)
        
        #variation throughout the day
        cold_feed_schedulem += [[
        Teveningm - delta * t/6 for t in range(0,6)]+
        [Teveningm - (15-t) * delta /9 for t in range(6,15)]+
        [Teveningm for t in range(15,24)]]
        
    outputfeedtemp=[]
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[0])
    for i in range(28):
        outputfeedtemp.extend(cold_feed_schedulem[1])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[2])
    for i in range(30):
        outputfeedtemp.extend(cold_feed_schedulem[3])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[4])
    for i in range(30):
        outputfeedtemp.extend(cold_feed_schedulem[5])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[6])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[7])
    for i in range(30):
        outputfeedtemp.extend(cold_feed_schedulem[8])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[9])
    for i in range(30):
        outputfeedtemp.extend(cold_feed_schedulem[10])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[11])
    
    project_dict['ColdWaterSource'][feedtype] = {
        "start_day": 0,
        "time_series_step": 1,
        "temperatures": outputfeedtemp
    }
    return outputfeedtemp
