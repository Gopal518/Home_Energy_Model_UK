#!/usr/bin/env python3

"""
This module reads in an energy + weather file.
"""

import csv
from enum import Enum

COLUMN_LONGITUDE = 7
COLUMN_LATITUDE = 6
COLUMN_AIR_TEMP = 6 # dry bulb temp in degrees
COLUMN_WIND_SPEED = 21 # wind speed in m/sec
COLUMN_DNI_RAD = 14 # direct beam normal irradiation in Wh/m2
COLUMN_DIF_RAD = 15 # diffuse irradiation (horizantal plane) in Wh/m2
COLUMN_GROUND_REFLECT = 32

def weather_data_to_dict(weather_file):
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
            if line_count == 0:
                longitude = float(row[COLUMN_LONGITUDE])
                latitude = float(row[COLUMN_LATITUDE])
            elif line_count >= 8:
                air_temperatures.append(float(row[COLUMN_AIR_TEMP]))
                wind_speeds.append(float(row[COLUMN_WIND_SPEED]))
                dir_beam_rad.append(float(row[COLUMN_DNI_RAD]))
                diff_hor_rad.append(float(row[COLUMN_DIF_RAD]))
                ground_solar_reflc.append(0.2)
            line_count = line_count + 1

    external_conditions = {
        "air_temperatures": air_temperatures,
        "wind_speeds": wind_speeds,
        "diffuse_horizontal_radiation": diff_hor_rad,
        "direct_beam_radiation": dir_beam_rad,
        "solar_reflectivity_of_ground": ground_solar_reflc,
        "longitude": longitude,
        "latitude": latitude,
        #conversion is not needed as direct irradiation will be normal plane from this file
        "direct_beam_conversion_needed": False 
        }

    return external_conditions
