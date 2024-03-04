#!/usr/bin/env python3

"""
This module reads in weather data from CIBSE csv file.
"""

import csv
from enum import Enum
import core.units as units

COLUMN_LONGITUDE = 3
COLUMN_LATITUDE = 1
COLUMN_AIR_TEMP = 6 # dry bulb temp in degrees
COLUMN_WIND_SPEED = 11 # in knots
COLUMN_GHI_RAD = 12 # global irradiation (horizantal plane) in Wh/m2
#COLUMN_DNI_RAD = # direct beam normal irradiation in Wh/m2 NOT IN FILE
#COLUMN_DIR_RAD = # direct beam (horizontal plane) irradiation in Wh/m2 NOT IN FILE
COLUMN_DIF_RAD = 13 # diffuse irradiation (horizantal plane) in Wh/m2
#COLUMN_GROUND_REFLECT = # NOT IN FILE. Using 0.2 default

def CIBSE_weather_data_to_dict(weather_file):
    """ Read in weather file, return dictionary"""
    air_temperatures = []
    wind_speeds = []
    diff_hor_rad = []
    dir_beam_rad = []
    ground_solar_reflc = []

    with open(weather_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter = ',')
        line_count = 0
        for row in csv_reader:
            if line_count == 5:
                longitude = float(row[COLUMN_LONGITUDE])
                latitude = float(row[COLUMN_LATITUDE])
            elif line_count >= 32:
                air_temperatures.append(float(row[COLUMN_AIR_TEMP]))
                wind_speeds.append(float(row[COLUMN_WIND_SPEED]) / units.knots_per_m_per_sec)
                #no DNI direct irradiation in file need to extract from global and diffuse values
                global_horiz_irr = float(row[COLUMN_GHI_RAD])
                diffuse_horiz_irr = float(row[COLUMN_DIF_RAD])
                dir_beam_rad.append(global_horiz_irr - diffuse_horiz_irr)
                diff_hor_rad.append(float(row[COLUMN_DIF_RAD]))
                ground_solar_reflc.append(float(0.2))
            line_count = line_count + 1

    external_conditions = {
        "air_temperatures": air_temperatures,
        "wind_speeds": wind_speeds,
        "diffuse_horizontal_radiation": diff_hor_rad,
        "direct_beam_radiation": dir_beam_rad,
        "solar_reflectivity_of_ground": ground_solar_reflc,
        "longitude": longitude,
        "latitude": latitude,
        #conversion is needed as direct irradiation will be horizontal not normal from this file
        "direct_beam_conversion_needed": True 
        }

    return external_conditions

