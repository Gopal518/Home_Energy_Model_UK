#!/usr/bin/env python3

"""
This module provides the entry point to the program and defines the command-line interface.
"""

# Standard library imports
import sys
import json
import csv
import os
import shutil
import argparse
from math import floor

# Third-party imports
import numpy as np

# Local imports
from core.project import Project
import core.units as units
from read_weather_file import weather_data_to_dict
from read_CIBSE_weather_file import CIBSE_weather_data_to_dict
from wrappers.future_homes_standard.future_homes_standard import \
    apply_fhs_preprocessing, apply_fhs_postprocessing
from wrappers.future_homes_standard.future_homes_standard_notional import \
    apply_fhs_not_preprocessing
from wrappers.future_homes_standard.future_homes_standard_FEE import \
    apply_fhs_FEE_preprocessing, apply_fhs_FEE_postprocessing


def run_project(
        inp_filename,
        external_conditions_dict,
        preproc_only=False,
        fhs_assumptions=False,
        fhs_FEE_assumptions=False,
        fhs_notA_assumptions=False,
        fhs_notB_assumptions=False,
        fhs_FEE_notA_assumptions=False,
        fhs_FEE_notB_assumptions=False,
        heat_balance=False,
        detailed_output_heating_cooling=False,
        use_fast_solver=False,
        ):
    file_name = os.path.splitext(os.path.basename(inp_filename))[0]
    file_path = os.path.splitext(os.path.abspath(inp_filename))[0]
    results_folder = os.path.join(file_path + '__results', '')
    os.makedirs(results_folder, exist_ok=True)
    if fhs_assumptions:
        output_file_run_name = 'FHS'
    elif fhs_FEE_assumptions:
        output_file_run_name = 'FHS_FEE'
    elif fhs_notA_assumptions:
        output_file_run_name = 'FHS_notA'
    elif fhs_notB_assumptions:
        output_file_run_name = 'FHS_notB'
    elif fhs_FEE_notA_assumptions:
        output_file_run_name = 'FHS_FEE_notA'
    elif fhs_FEE_notB_assumptions:
        output_file_run_name = 'FHS_FEE_notB'
    else:
        output_file_run_name = 'core'

    output_file_name_stub = results_folder + file_name + '__' + output_file_run_name + '__'
    output_file_detailed = output_file_name_stub + 'results.csv'
    output_file_static = output_file_name_stub + 'results_static.csv'
    output_file_summary = output_file_name_stub + 'results_summary.csv'
    print(inp_filename)
    with open(inp_filename) as json_file:
        project_dict = json.load(json_file)

    if external_conditions_dict is not None:
        # Note: Shading segments are an assessor input regardless, so save them
        # before overwriting the ExternalConditions and re-insert after
        shading_segments = project_dict["ExternalConditions"]["shading_segments"]
        project_dict["ExternalConditions"] = external_conditions_dict
        project_dict["ExternalConditions"]["shading_segments"] = shading_segments

    # Apply required preprocessing steps, if any
    # TODO Implement notional runs (the below treats them the same as the
    #      equivalent non-notional runs)
    if fhs_notA_assumptions or fhs_notB_assumptions \
    or fhs_FEE_notA_assumptions or fhs_FEE_notB_assumptions:
        print('applying_fhs_not_preprocessing')
        project_dict = apply_fhs_not_preprocessing(project_dict, 
                                                   fhs_notA_assumptions, 
                                                   fhs_notB_assumptions,
                                                   fhs_FEE_notA_assumptions,
                                                   fhs_FEE_notB_assumptions)
    if fhs_assumptions or fhs_notA_assumptions or fhs_notB_assumptions:
        print('applying_fhs_preprocessing')
        project_dict = apply_fhs_preprocessing(project_dict)
    elif fhs_FEE_assumptions or fhs_FEE_notA_assumptions or fhs_FEE_notB_assumptions:
        print('apply_fhs_FEE_preprocessing')
        project_dict = apply_fhs_FEE_preprocessing(project_dict)

    if preproc_only:
        preproc_file_name = output_file_name_stub + 'preproc.json'
        with open(preproc_file_name, 'w') as preproc_file:
            json.dump(project_dict, preproc_file, sort_keys=True, indent=4)
        shutil.copy2(inp_filename, results_folder)
        return # Skip actual calculation if preproc only option has been selected

    project = Project(project_dict, heat_balance, detailed_output_heating_cooling, use_fast_solver)

    # Calculate static parameters and output
    heat_trans_coeff, heat_loss_param, HTC_dict, HLP_dict = project.calc_HTC_HLP()
    heat_capacity_param = project.calc_HCP()
    heat_loss_form_factor = project.calc_HLFF()
    write_static_output_file(
        output_file_static,
        heat_trans_coeff,
        heat_loss_param,
        heat_capacity_param,
        heat_loss_form_factor,
        )

    # Run main simulation
    timestep_array, results_totals, results_end_user, \
        energy_import, energy_export, energy_generated_consumed, \
        energy_to_storage, energy_from_storage, energy_diverted, betafactor, \
        zone_dict, zone_list, hc_system_dict, hot_water_dict, \
        heat_cop_dict, cool_cop_dict, dhw_cop_dict, \
        ductwork_gains, heat_balance_dict, heat_source_wet_results_dict, \
        heat_source_wet_results_annual_dict \
        = project.run()

    write_core_output_file(
        output_file_detailed,
        timestep_array,
        results_totals,
        results_end_user,
        energy_import,
        energy_export,
        energy_generated_consumed,
        energy_to_storage,
        energy_from_storage,
        energy_diverted,
        betafactor,
        zone_dict,
        zone_list,
        hc_system_dict,
        hot_water_dict,
        ductwork_gains
        )

    if heat_balance:
        hour_per_step = project_dict['SimulationTime']['step']
        for hb_name, hb_dict in heat_balance_dict.items():
            heat_balance_output_file = output_file_name_stub + 'results_heat_balance_' + hb_name + '.csv'
            write_heat_balance_output_file(
                heat_balance_output_file,
                timestep_array,
                hour_per_step,
                hb_dict,
                )

    if detailed_output_heating_cooling:
        for heat_source_wet_name, heat_source_wet_results in heat_source_wet_results_dict.items():
            heat_source_wet_output_file \
                = output_file_name_stub + 'results_heat_source_wet__' \
                + heat_source_wet_name + '.csv'
            write_heat_source_wet_output_file(
                heat_source_wet_output_file,
                timestep_array,
                heat_source_wet_results,
                )
        for heat_source_wet_name, heat_source_wet_results_annual \
            in heat_source_wet_results_annual_dict.items():
            heat_source_wet_output_file \
                = output_file_name_stub + 'results_heat_source_wet_summary__' \
                + heat_source_wet_name + '.csv'
            write_heat_source_wet_summary_output_file(
                heat_source_wet_output_file,
                heat_source_wet_results_annual,
                )

    # Sum per-timestep figures as needed
    space_heat_demand_total = sum(sum(h_dem) for h_dem in zone_dict['Space heat demand'].values())
    space_cool_demand_total = sum(sum(c_dem) for c_dem in zone_dict['Space cool demand'].values())
    total_floor_area = project.total_floor_area()
    daily_hw_demand = units.convert_profile_to_daily(
        hot_water_dict['Hot water energy demand incl pipework_loss']['energy_demand_incl_pipework_loss'],
        project_dict['SimulationTime']['step'],
        )
    daily_hw_demand_75th_percentile = np.percentile(daily_hw_demand, 75)

    write_core_output_file_summary(
        output_file_summary,
        project_dict,
        timestep_array,
        results_end_user,
        energy_generated_consumed,
        energy_to_storage,
        energy_from_storage,
        energy_diverted,
        energy_import,
        energy_export,
        space_heat_demand_total,
        space_cool_demand_total,
        total_floor_area,
        heat_cop_dict,
        cool_cop_dict,
        dhw_cop_dict,
        daily_hw_demand_75th_percentile,
        )

    # Apply required postprocessing steps, if any
    if fhs_assumptions or fhs_notA_assumptions or fhs_notB_assumptions:
        if fhs_notA_assumptions or fhs_notB_assumptions:
            notional = True
        else:
            notional = False
        apply_fhs_postprocessing(
            project_dict,
            results_totals,
            energy_import,
            energy_export,
            results_end_user,
            timestep_array,
            output_file_name_stub,
            notional,
            )
    elif fhs_FEE_assumptions or fhs_FEE_notA_assumptions or fhs_FEE_notB_assumptions:
        postprocfile = output_file_name_stub + 'postproc.csv'
        apply_fhs_FEE_postprocessing(
            postprocfile,
            total_floor_area,
            space_heat_demand_total,
            space_cool_demand_total,
            )

    shutil.copy2(inp_filename, results_folder)

def write_static_output_file(
        output_file,
        heat_trans_coeff,
        heat_loss_param,
        heat_capacity_param,
        heat_loss_form_factor,
        ):
    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Heat transfer coefficient', 'W / K', heat_trans_coeff])
        writer.writerow(['Heat loss parameter', 'W / m2.K', heat_loss_param])
        writer.writerow(['Heat capacity parameter', 'kJ / m2.K', heat_capacity_param])
        writer.writerow(['Heat loss form factor','',heat_loss_form_factor])

def write_heat_balance_output_file(
        heat_balance_output_file,
        timestep_array,
        hour_per_step,
        heat_balance_dict,
        ):
    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(heat_balance_output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        headings = ['Timestep']
        units_row = ['index']
        rows = ['']

        headings_annual = ['']
        units_annual = ['']

        nbr_of_zones = 0
        for z_name, heat_loss_gain_dict in heat_balance_dict.items():
            for heat_loss_gain_name in heat_loss_gain_dict.keys():
                headings.append(z_name+': '+heat_loss_gain_name)
                units_row.append('[W]')
            nbr_of_zones += 1

        for z_name, heat_loss_gain_dict in heat_balance_dict.items():
            annual_totals = [0]*(len(heat_loss_gain_dict.keys())*nbr_of_zones)
            annual_totals.insert(0,'')
            for heat_loss_gain_name in heat_loss_gain_dict.keys():
                headings_annual.append(z_name+': total '+heat_loss_gain_name)
                units_annual.append('[kWh]')

        for t_idx, timestep in enumerate(timestep_array):
            row = [t_idx]
            annual_totals_index = 1
            for z_name, heat_loss_gain_dict in heat_balance_dict.items():
                for heat_loss_gain_name in heat_loss_gain_dict.keys():
                    row.append(heat_loss_gain_dict[heat_loss_gain_name][t_idx])
                    annual_totals[annual_totals_index] += \
                        heat_loss_gain_dict[heat_loss_gain_name][t_idx]*hour_per_step/units.W_per_kW
                    annual_totals_index += 1
            rows.append(row)

        writer.writerow(headings_annual)
        writer.writerow(units_annual)
        writer.writerow(annual_totals)
        writer.writerow([''])
        writer.writerow(headings)
        writer.writerow(units_row)
        writer.writerows(rows)

def write_heat_source_wet_output_file(output_file, timestep_array, heat_source_wet_results):

    # Repeat column headings for each service
    col_headings = ['Timestep count']
    col_units_row = ['']
    columns = {}
    for service_name, service_results in heat_source_wet_results.items():
        columns[service_name] = [col for col in service_results.keys()]
        col_headings += [col_heading for col_heading, _ in columns[service_name]]
        col_units_row += [col_unit for _, col_unit in columns[service_name]]

    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Write column headings and units
        writer.writerow(col_headings)
        writer.writerow(col_units_row)

        # Write rows
        for t_idx in range(0, len(timestep_array)):
            row = [t_idx]
            for service_name, service_results in heat_source_wet_results.items():
                row += [service_results[col][t_idx] for col in columns[service_name]]
            writer.writerow(row)

def write_heat_source_wet_summary_output_file(output_file, heat_source_wet_results_annual):
    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        for service_name, service_results in heat_source_wet_results_annual.items():
            writer.writerow((service_name,))
            for name, value in service_results.items():
                writer.writerow((name[0], name[1], value))
            writer.writerow('')

def write_core_output_file(
        output_file,
        timestep_array,
        results_totals,
        results_end_user,
        energy_import,
        energy_export,
        energy_generated_consumed,
        energy_to_storage,
        energy_from_storage,
        energy_diverted,
        betafactor,
        zone_dict,
        zone_list,
        hc_system_dict,
        hot_water_dict,
        ductwork_gains
        ):
    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        headings = ['Timestep']
        units_row = ['[count]']
        for totals_key in results_totals.keys():
            totals_header = str(totals_key)
            totals_header = totals_header + ' total'
            headings.append(totals_header)
            units_row.append('[kWh]')
            for end_user_key in results_end_user[totals_key].keys():
                headings.append(end_user_key)
                units_row.append('[kWh]')
            headings.append(str(totals_key) + ' import')
            units_row.append('[kWh]')
            headings.append(str(totals_key) + ' export')
            units_row.append('[kWh]')
            headings.append(str(totals_key) + ' generated and consumed')
            units_row.append('[kWh]')
            headings.append(str(totals_key) + ' beta factor')
            units_row.append('[ratio]')
            headings.append(str(totals_key) + ' to storage')
            units_row.append('[kWh]')
            headings.append(str(totals_key) + ' from storage')
            units_row.append('[kWh]')
            headings.append(str(totals_key) + ' diverted')
            units_row.append('[kWh]')

        # Dictionary for most of the units (future output headings need respective units)
        unitsDict = {
            'Internal gains': '[W]',
            'Solar gains': '[W]',
            'Operative temp': '[deg C]',
            'Internal air temp': '[deg C]',
            'Space heat demand': '[kWh]',
            'Space cool demand': '[kWh]',
            'Hot water demand': '[litres]',
            'Hot water energy demand': '[kWh]',
            'Hot water duration': '[mins]',
            'Hot Water Events': '[count]',
            'Pipework losses': '[kWh]'
        }

        for zone in zone_list:
            for zone_outputs in zone_dict.keys():
                zone_headings = zone_outputs + ' ' + zone
                headings.append(zone_headings)
                if zone_outputs in unitsDict:
                    units_row.append(unitsDict.get(zone_outputs))
                else:
                    this_filename = os.path.basename(__file__)
                    units_row.append('Unit not defined (unitsDict ' + this_filename + ')')

        for system in hc_system_dict:
            for hc_name in hc_system_dict[system].keys():
                if hc_name == None:
                    hc_name = 'None'
                    hc_system_headings = system + ' ' + hc_name
                else:
                    hc_system_headings = system + ' ' + hc_name
                headings.append(hc_system_headings)
                units_row.append('[kWh]')
        #Hot_water_dict headings
        for system in hot_water_dict:
            headings.append(system)
            if system in unitsDict:
                units_row.append(unitsDict.get(system))
            else:
                this_filename = os.path.basename(__file__)
                units_row.append('Unit not defined (add to unitsDict ' + this_filename + ')')

        headings.append('Ductwork gains')
        units_row.append('[kWh]')

        # Write headings & units to output file
        writer.writerow(headings)
        writer.writerow(units_row)

        for t_idx, timestep in enumerate(timestep_array):
            energy_use_row = []
            zone_row = []
            hc_system_row = []
            hw_system_row = []
            hw_system_row_energy = []
            hw_system_row_duration = []
            hw_system_row_events = []
            pw_losses_row = []
            ductwork_row = []
            energy_shortfall = []
            i = 0
            # Loop over end use totals
            for totals_key in results_totals:
                energy_use_row.append(results_totals[totals_key][t_idx])
                for end_user_key in results_end_user[totals_key]:
                    energy_use_row.append(results_end_user[totals_key][end_user_key][t_idx])
                energy_use_row.append(energy_import[totals_key][t_idx])
                energy_use_row.append(energy_export[totals_key][t_idx])
                energy_use_row.append(energy_generated_consumed[totals_key][t_idx])
                energy_use_row.append(betafactor[totals_key][t_idx])
                energy_use_row.append(energy_to_storage[totals_key][t_idx])
                energy_use_row.append(energy_from_storage[totals_key][t_idx])
                energy_use_row.append(energy_diverted[totals_key][t_idx])

                # Loop over results separated by zone
            for zone in zone_list:
                for zone_outputs in zone_dict:
                    zone_row.append(zone_dict[zone_outputs][zone][t_idx])
                # Loop over heating and cooling system demand
            for system in hc_system_dict:
                for hc_name in hc_system_dict[system]:
                    hc_system_row.append(hc_system_dict[system][hc_name][t_idx])

            # loop over hot water demand
            hw_system_row.append(hot_water_dict['Hot water demand']['demand'][t_idx])
            hw_system_row_energy.append(hot_water_dict['Hot water energy demand']['energy_demand'][t_idx])
            hw_system_row_duration.append(hot_water_dict['Hot water duration']['duration'][t_idx])
            pw_losses_row.append(hot_water_dict['Pipework losses']['pw_losses'][t_idx])
            hw_system_row_events.append(hot_water_dict['Hot Water Events']['no_events'][t_idx])
            ductwork_row.append(ductwork_gains['ductwork_gains'][t_idx])

            # create row of outputs and write to output file
            row = [t_idx] + energy_use_row + zone_row + hc_system_row + \
            hw_system_row + hw_system_row_energy + hw_system_row_duration + \
            hw_system_row_events + pw_losses_row + ductwork_row + energy_shortfall
            writer.writerow(row)

def write_core_output_file_summary(
        output_file_summary,
        project_dict,
        timestep_array,
        results_end_user,
        energy_generated_consumed,
        energy_to_storage,
        energy_from_storage,
        energy_diverted,
        energy_import,
        energy_export,
        space_heat_demand_total,
        space_cool_demand_total,
        total_floor_area,
        heat_cop_dict,
        cool_cop_dict,
        dhw_cop_dict,
        daily_hw_demand_75th_percentile,
        ):
    # Electricity breakdown
    elec_generated = 0
    elec_consumed = 0
    for end_use, arr in results_end_user['mains elec'].items():
        if sum(arr)<0:
            elec_generated+=abs(sum(arr))
        else:
            elec_consumed+=sum(arr)
    
    gen_to_consumption = sum(energy_generated_consumed['mains elec'])
    grid_to_consumption = sum(energy_import['mains elec'])
    generation_to_grid = abs(sum(energy_export['mains elec']))
    net_import = grid_to_consumption - generation_to_grid
    gen_to_storage = sum(energy_to_storage['mains elec'])
    storage_to_consumption = abs(sum(energy_from_storage['mains elec']))
    gen_to_diverter = sum(energy_diverted['mains elec'])
    if gen_to_storage > 0.0:
        storage_eff = storage_to_consumption / gen_to_storage
    else:
        storage_eff = 'DIV/0'

    #get peak electrcitiy consumption, and when it happens
    start_timestep=project_dict['SimulationTime']['start']
    stepping = project_dict['SimulationTime']['step']
    # Calculate net import by adding gross import and export figures. Add
    # because export figures are already negative
    net_import_per_timestep = [
        energy_import['mains elec'][i] + energy_export['mains elec'][i]
        for i in range(len(timestep_array))
        ]
    peak_elec_consumption = max(net_import_per_timestep)
    index_peak_elec_consumption = net_import_per_timestep.index(peak_elec_consumption)
    #must reflect hour or half hour in the year (hour 0 to hour 8759)
    #to work with the dictionary below timestep_to_date
    #hence + start_timestep
    step_peak_elec_consumption = index_peak_elec_consumption + start_timestep
    
    HOURS_TO_END_JAN = 744
    HOURS_TO_END_FEB = 1416
    HOURS_TO_END_MAR = 2160
    HOURS_TO_END_APR = 2880
    HOURS_TO_END_MAY = 3624
    HOURS_TO_END_JUN = 4344
    HOURS_TO_END_JUL = 5088
    HOURS_TO_END_AUG = 5832
    HOURS_TO_END_SEP = 6552
    HOURS_TO_END_OCT = 7296
    HOURS_TO_END_NOV = 8016
    HOURS_TO_END_DEC = 8760
    months_start_end_timesteps = {'JAN':(0,HOURS_TO_END_JAN/stepping-1),
                                  'FEB':(HOURS_TO_END_JAN/stepping,HOURS_TO_END_FEB/stepping-1),
                                  'MAR':(HOURS_TO_END_FEB/stepping,HOURS_TO_END_MAR/stepping-1),
                                  'APR':(HOURS_TO_END_MAR/stepping,HOURS_TO_END_APR/stepping-1),
                                  'MAY':(HOURS_TO_END_APR/stepping,HOURS_TO_END_MAY/stepping-1),
                                  'JUN':(HOURS_TO_END_MAY/stepping,HOURS_TO_END_JUN/stepping-1),
                                  'JUL':(HOURS_TO_END_JUN/stepping,HOURS_TO_END_JUL/stepping-1),
                                  'AUG':(HOURS_TO_END_JUL/stepping,HOURS_TO_END_AUG/stepping-1),
                                  'SEP':(HOURS_TO_END_AUG/stepping,HOURS_TO_END_SEP/stepping-1),
                                  'OCT':(HOURS_TO_END_SEP/stepping,HOURS_TO_END_OCT/stepping-1),
                                  'NOV':(HOURS_TO_END_OCT/stepping,HOURS_TO_END_NOV/stepping-1),
                                  'DEC':(HOURS_TO_END_NOV/stepping,HOURS_TO_END_DEC/stepping-1)}
    timestep_to_date = {}
    #the step must reflect hour or half hour in the year (hour 0 to hour 8759)
    #step starts on the start_timestep 
    step = start_timestep
    for hour_of_year in timestep_array:
        for month,start_end in months_start_end_timesteps.items():
            if step<=int(start_end[1]) and step>=int(start_end[0]):
                hour_of_year = step * stepping
                hour_start_month = start_end[0] * stepping
                hour_of_month = hour_of_year - hour_start_month
                #add +1 to day_of_month for first day to be day 1 (not day 0)
                day_of_month = floor(hour_of_month/24) + 1
                #add +1 to hour_of_month for first hour to be hour 1 (not hour 0)
                hour_of_day = (step % (24 / stepping)) * stepping + 1
                timestep_to_date[step]={'month':month,'day':day_of_month,'hour':hour_of_day}
        step +=1
    
    # Delivered energy by end-use and by fuel
    delivered_energy_dict = {'total':{'total':0}}
    for fuel,end_uses in results_end_user.items():
        if fuel not in ['_unmet_demand','hw cylinder']:
            delivered_energy_dict[fuel]={}
            delivered_energy_dict[fuel]['total'] = 0
            for end_use,delivered_energy in end_uses.items():
                if sum(delivered_energy)>=0:
                    delivered_energy_dict[fuel][end_use]=sum(delivered_energy)
                    delivered_energy_dict[fuel]['total'] +=sum(delivered_energy)
                    if end_use not in delivered_energy_dict['total'].keys():
                        delivered_energy_dict['total'][end_use] = sum(delivered_energy)
                    else:
                        delivered_energy_dict['total'][end_use] += sum(delivered_energy)
                    delivered_energy_dict['total']['total'] +=sum(delivered_energy)
    
    delivered_energy_rows_title = ['Delivered energy by end-use (below) and fuel (right) [kWh/m2]']
    delivered_energy_rows = [['total']]
    for fuel, end_uses in delivered_energy_dict.items():
        delivered_energy_rows_title.append(fuel)
        for row in delivered_energy_rows:
            row.append(0)
        for end_use,value in end_uses.items():
            end_use_found = False
            for row in delivered_energy_rows:
                if end_use in row:
                    end_use_found = True
                    row[delivered_energy_rows_title.index(fuel)] = value/total_floor_area
            if not end_use_found:
                new_row = [0]*len(delivered_energy_rows_title)
                new_row[0] = end_use
                new_row[delivered_energy_rows_title.index(fuel)] = value/total_floor_area
                delivered_energy_rows.append(new_row)

    heat_cop_rows = [(h_name, h_cop) for h_name, h_cop in heat_cop_dict.items()]
    cool_cop_rows = [(c_name, c_cop) for c_name, c_cop in cool_cop_dict.items()]
    dhw_cop_rows = [[hw_name, hw_cop] for hw_name, hw_cop in dhw_cop_dict.items()]

    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file_summary, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Energy Demand Summary'])
        writer.writerow(['', '', 'Total'])
        writer.writerow(['Space heat demand', 'kWh/m2', space_heat_demand_total/total_floor_area])
        writer.writerow(['Space cool demand', 'kWh/m2', space_cool_demand_total/total_floor_area])
        writer.writerow([])
        writer.writerow(['Electricity Summary'])
        writer.writerow(['','kWh','timestep','month','day','hour of day'])
        writer.writerow(['Peak half-hour consumption',
                         peak_elec_consumption,
                         index_peak_elec_consumption,
                         timestep_to_date[step_peak_elec_consumption]['month'],
                         timestep_to_date[step_peak_elec_consumption]['day'],
                         timestep_to_date[step_peak_elec_consumption]['hour']
                         ])
        writer.writerow(['','','Total'])
        writer.writerow(['Consumption','kWh',elec_consumed])
        writer.writerow(['Generation','kWh',elec_generated])
        writer.writerow([
            'Generation to consumption (immediate, excl. diverter)',
            'kWh',
            gen_to_consumption,
            ])
        writer.writerow(['Generation to storage', 'kWh', gen_to_storage])
        writer.writerow(['Generation to diverter', 'kWh', gen_to_diverter])
        writer.writerow(['Generation to grid (export)','kWh',generation_to_grid])
        writer.writerow(['Storage to consumption', 'kWh', storage_to_consumption])
        writer.writerow(['Grid to consumption (import)','kWh',grid_to_consumption])
        writer.writerow(['Net import','kWh',net_import])
        writer.writerow(['Storage round-trip efficiency', 'ratio', storage_eff])
        writer.writerow([])
        writer.writerow(['Delivered Energy Summary'])
        writer.writerow(delivered_energy_rows_title)
        writer.writerows(delivered_energy_rows)
        if dhw_cop_rows:
            writer.writerow([])
            writer.writerow([
                'Hot water system',
                'Overall CoP',
                'Daily HW demand (kWh, 75th percentile)',
                'HW cylinder volume (litres)',
                ])
            for row in dhw_cop_rows:
                row.append(daily_hw_demand_75th_percentile)
                if project_dict['HotWaterSource'][row[0]]['type'] == 'StorageTank':
                    row.append(project_dict['HotWaterSource'][row[0]]['volume'])
                else:
                    row.append('N/A')
            writer.writerows(dhw_cop_rows)
        if heat_cop_rows:
            writer.writerow([])
            writer.writerow(['Space heating system', 'Overall CoP'])
            writer.writerows(heat_cop_rows)
        if cool_cop_rows:
            writer.writerow([])
            writer.writerow(['Space cooling system', 'Overall CoP'])
            writer.writerows(cool_cop_rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Home Energy Model (HEM)')
    parser.add_argument(
        '--epw-file', '-w',
        action='store',
        default="/home/ml/HarshSir/GBR_ENG_Southampton.epw",
        help=('path to weather file in .epw format'),
        )
    parser.add_argument(
        '--CIBSE-weather-file',
        action='store',
        default=None,
        help=('path to CIBSE weather file in .csv format'),
        )
    parser.add_argument(
        '--input_file',
        action='store',
        default= "test/demo_files/core/demo.json",
        help=('path(s) to file(s) containing building specifications to run'),
        )
    parser.add_argument(
        '--parallel', '-p',
        action='store',
        type=int,
        default=0,
        help=('run calculations for different input files in parallel'
              '(specify no of files to run simultaneously)'),
        )
    parser.add_argument(
        '--preprocess-only',
        action='store_true',
        default=False,
        help='run prepocessing step only',
        )
    wrapper_options = parser.add_mutually_exclusive_group()
    wrapper_options.add_argument(
        '--future-homes-standard',
        action='store_true',
        default=False,
        help='use Future Homes Standard calculation assumptions',
        )
    wrapper_options.add_argument(
        '--future-homes-standard-FEE',
        action='store_true',
        default=False,
        help='use Future Homes Standard Fabric Energy Efficiency assumptions',
        )
    wrapper_options.add_argument(
        '--future-homes-standard-notA',
        action='store_true',
        default=False,
        help='use Future Homes Standard calculation assumptions for notional option A',
        )
    wrapper_options.add_argument(
        '--future-homes-standard-notB',
        action='store_true',
        default=False,
        help='use Future Homes Standard calculation assumptions for notional option B',
        )
    wrapper_options.add_argument(
        '--future-homes-standard-FEE-notA',
        action='store_true',
        default=False,
        help='use Future Homes Standard Fabric Energy Efficiency assumptions for notional option A',
        )
    wrapper_options.add_argument(
        '--future-homes-standard-FEE-notB',
        action='store_true',
        default=False,
        help='use Future Homes Standard Fabric Energy Efficiency assumptions for notional option B',
        )
    parser.add_argument(
        '--heat-balance',
        action='store_true',
        default=False,
        help='output heat balance for each zone',
        )
    parser.add_argument(
        '--detailed-output-heating-cooling',
        action='store_true',
        default=False,
        help=('output detailed calculation results for heating and cooling '
              'system objects (including HeatSourceWet objects) where the '
              'relevant objects have this functionality'
              )
        )
    parser.add_argument(
        '--no-fast-solver',
        action='store_true',
        default=False,
        help=('disable optimised solver (results may differ slightly due '
              'to reordering of floating-point ops); this option is '
              'provided to facilitate verification and debugging of the '
              'optimised version')
        )
    cli_args = parser.parse_args()

    inp_filenames = ["test/demo_files/core/demo.json"]
    epw_filename = "/home/ml/HarshSir/GBR_ENG_Southampton.epw"
    cibse_weather_filename = cli_args.CIBSE_weather_file
    fhs_assumptions = cli_args.future_homes_standard
    fhs_FEE_assumptions = cli_args.future_homes_standard_FEE
    fhs_notA_assumptions = cli_args.future_homes_standard_notA
    fhs_notB_assumptions = cli_args.future_homes_standard_notB
    fhs_FEE_notA_assumptions = cli_args.future_homes_standard_FEE_notA
    fhs_FEE_notB_assumptions = cli_args.future_homes_standard_FEE_notB
    preproc_only = cli_args.preprocess_only
    heat_balance = cli_args.heat_balance
    detailed_output_heating_cooling = cli_args.detailed_output_heating_cooling
    use_fast_solver = not cli_args.no_fast_solver

    if epw_filename is not None:
        external_conditions_dict = weather_data_to_dict(epw_filename)
    elif cibse_weather_filename is not None:
        external_conditions_dict = CIBSE_weather_data_to_dict(cibse_weather_filename)
    
    else:
        external_conditions_dict = None

    if cli_args.parallel == 0:
        print('Running '+str(len(inp_filenames))+' cases in series')
        for inpfile in inp_filenames:
            run_project(
                inpfile,
                external_conditions_dict,
                preproc_only,
                fhs_assumptions,
                fhs_FEE_assumptions,
                fhs_notA_assumptions,
                fhs_notB_assumptions,
                fhs_FEE_notA_assumptions,
                fhs_FEE_notB_assumptions,
                heat_balance,
                detailed_output_heating_cooling,
                use_fast_solver,
                )
    else:
        import multiprocessing as mp
        print('Running '+str(len(inp_filenames))+' cases in parallel'
              ' ('+str(cli_args.parallel)+' at a time)')
        run_project_args = [
            ( inpfile,
              external_conditions_dict,
              preproc_only,
              fhs_assumptions,
              fhs_FEE_assumptions,
              heat_balance,
              detailed_output_heating_cooling,
              use_fast_solver,
            )
            for inpfile in inp_filenames
            ]
        with mp.Pool(processes=cli_args.parallel) as p:
            p.starmap(run_project, run_project_args)

