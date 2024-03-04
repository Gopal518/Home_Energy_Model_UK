#!/usr/bin/env python3

"""
This module provides functions to implement pre- and post-processing
steps for the Fabric Energy Efficiency calculation run for the Future Homes
Standard.
"""

# Standard library imports
import sys
import csv

# Local imports
from wrappers.future_homes_standard.future_homes_standard import \
    apply_fhs_preprocessing, calc_TFA
from wrappers.future_homes_standard.future_homes_standard_notional import \
    minimum_air_change_rate, energysupplyname_electricity

def apply_fhs_FEE_preprocessing(project_dict):
    # Calculation assumptions (expressed in comments) are based on SAP 10.2 FEE specification

    # Climate should be same as actual building, but weather data is external
    # to this program so it will have to specified by the user or user interface

    # No heat gain from pumps or fans. Water and space heating systems selected
    # have no pumps or fans, and the only ventilation fans are extract-only so
    # do not lead to heat gains either, so no additional action required for this

    # Window shading should be same as actual building, so no action required here

    # The number of each of the following is the same as the actual building, so
    # no action required here:
    # - open chimneys
    # - open flues
    # - chimneys/flues attached to closed fire
    # - flues attached to solid fuel boiler
    # - flues attached to other heater
    # - blocked chimneys
    # - passive vents
    # - flueless gas fires

    # No of intermittent extract fans is zero because there is continuous extract (see below)
    project_dict['Infiltration']['extract_fans'] = 0

    # Use continous decentralised mechanical extract ventilation
    total_floor_area = calc_TFA(project_dict)
    req_ach = minimum_air_change_rate(project_dict, total_floor_area) 
    project_dict['Ventilation'] = {
        'type': 'WHEV',
        'req_ach': req_ach,
        'SFP': 0.15,
        "EnergySupply": energysupplyname_electricity
        }

    # Use instantaneous electric water heater
    # Set power such that it should always be sufficient for any realistic demand
    # Look up cold water feed type
    # TODO The cold_water_source_name here needs to match the one defined in the
    #      standard FHS wrapper - ideally these would only be defined in one place
    if "header tank" in project_dict["ColdWaterSource"]:
        cold_water_source_name = "header tank"
    else:
        cold_water_source_name = "mains water"
    project_dict['HotWaterSource']['hw cylinder'] = {
        'type': 'PointOfUse',
        'power': 10000.0,
        'efficiency': 1.0,
        'EnergySupply': 'mains elec',
        'ColdWaterSource': cold_water_source_name,
        }
    # No hot water distribution pipework for point of use water heaters
    pipework_none = {
        'internal_diameter_mm': 0.01,
        'external_diameter_mm': 0.02,
        'length': 0.0,
        'insulation_thermal_conductivity': 0.01,
        'insulation_thickness_mm': 0.0,
        'surface_reflectivity': False,
        'pipe_contents': 'water'
        }
    project_dict['Distribution'] = {
        'internal': pipework_none,
        'external': pipework_none,
        }

    # One 9.3 kW InstantElecShower, one bath
    project_dict['Shower'] = {
        'IES_for_FEE_calc': {
            'type': 'InstantElecShower',
            'rated_power': 9.3,
            'EnergySupply': 'mains elec',
            'ColdWaterSource': cold_water_source_name,
            }
        }
    project_dict['Bath'] = {
        'bath for FEE calc': {
            'size': 73,
            'ColdWaterSource': cold_water_source_name,
            'flowrate': 12.0
            }
        }
    # Other tapping points have 6 litres/min flow rate. This shouldn't make any
    # difference to the space heating/cooling demand, as the number and flowrate
    # of the tapping points is only relevant for distribution losses, which do
    # not apply to point of use water heaters.
    project_dict['Other'] = {
        'Other HW for FEE calc': {
            "ColdWaterSource": cold_water_source_name,
            "flowrate": 6
        }
    }

    # Dwelling achieves water use target of not more than 125 litres/day
    project_dict['PartGcompliance'] = True

    # Remove WWHRS if present
    if 'WWHRS' in project_dict:
        del project_dict['WWHRS']

    # Lighting:
    # - capacity same as main FHS wrapper (so will be set in create_lighting_gains function)
    # - efficacy 120 lumens/W
    for z_name in project_dict['Zone'].keys():
        project_dict['Zone'][z_name]['Lighting']['efficacy'] = 120.0

    # Space heating from InstantElecHeater
    # Set power such that it should always be sufficient for any realistic demand
    # Assume convective fraction for fan heater from BS EN 15316-2:2017 Table B.17
    project_dict['SpaceHeatSystem'] = {}
    for z_name in project_dict['Zone'].keys():
        h_name = z_name + '_heating_for_FEE_calc'
        project_dict['Zone'][z_name]['SpaceHeatSystem'] = h_name
        project_dict['SpaceHeatSystem'][h_name] = {
            'type': 'InstantElecHeater',
            'rated_power': 10000.0,
            'frac_convective': 0.95,
            'EnergySupply': 'mains elec',
            }

    # Cooling from air conditioning
    # Set capacity such that it should always be sufficient for any realistic demand
    # Efficiency does not matter for this calc so set to 1.0
    # Assume convective fraction for cold air blowing system from BS EN 15316-2:2017 Table B.17
    project_dict['SpaceCoolSystem'] = {}
    for z_name in project_dict['Zone'].keys():
        c_name = z_name + '_cooling_for_FEE_calc'
        project_dict['Zone'][z_name]['SpaceCoolSystem'] = c_name
        project_dict['SpaceCoolSystem'][c_name] = {
            "type": "AirConditioning",
            "cooling_capacity": 10000.0,
            "efficiency": 1.0,
            "frac_convective": 0.95,
            "EnergySupply": "mains elec",
        }

    # Use control type 2 (seperate temperature control but no separate time control)
    project_dict["HeatingControlType"] = "SeparateTempControl"

    # Remove on-site generation, diverter and electric battery, if present
    if 'OnSiteGeneration' in project_dict:
        del project_dict['OnSiteGeneration']
    for energy_supply in project_dict['EnergySupply'].values():
        if 'diverter' in energy_supply:
            del energy_supply['diverter']
        if 'ElectricBattery' in energy_supply:
            del energy_supply['ElectricBattery']

    # Apply standard FHS preprocessing assumptions. Note these should be applied
    # after the other adjustments are made, because decisions may be based on
    # e.g. the heating system type.
    # Note: In SAP 10.2, different gains assumptions were used for the cooling
    # calculation compared to the heating calculation. However, only one set of
    # standardised gains have so far been defined here.
    project_dict = apply_fhs_preprocessing(project_dict)

    return project_dict

def apply_fhs_FEE_postprocessing(
        output_file,
        total_floor_area,
        space_heat_demand_total,
        space_cool_demand_total,
        ):
    # Subtract cooling demand from heating demand because cooling demand is negative by convention
    fabric_energy_eff = (space_heat_demand_total - space_cool_demand_total) / total_floor_area

    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Fabric Energy Efficiency', 'kWh / m2.yr', fabric_energy_eff])
