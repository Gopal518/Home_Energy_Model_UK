import math
import statistics
import sys
import os
import json
import numpy as np
import csv
import copy

this_directory = os.path.dirname(os.path.relpath(__file__))

sys.path.append(os.path.dirname(os.path.abspath(__file__))[:len(str("wrappers/future_homes_standard"))])
#need to run from sap11 venv or these will fail
from wrappers.future_homes_standard.future_homes_standard import calc_TFA, calc_N_occupants, \
HW_event_adjust_allocate, create_hot_water_use_pattern, create_cold_water_feed_temps
from wrappers.future_homes_standard.FHS_HW_events import HW_events_generator

'''
script for calculating calibration DHW volumes for each decile band
'''

decilebandingfile =  os.path.join(this_directory, "decile_banding.csv")
decileeventsfile =  os.path.join(this_directory, "day_of_week_events_by_decile.csv")
decileeventtimesfile =  os.path.join(this_directory, "day_of_week_events_by_decile_event_times.csv")

seedrange = range(0,1000)
headers = []
updated_rows = []

with open(decilebandingfile,'r') as bandsfile:
	bandsfilereader = csv.DictReader(bandsfile)
	print("median_daily_vol - calibration__vol - calibration_dhw_variance")
	#TODO this is slow and could be parallelised, but it only needs to be run when changes are made to the
	#HW events generation code - not on every run of the FHS wrapper
	for row in bandsfilereader:
		testvol = [0 for x in seedrange]
		for seed in seedrange:
			HWtest = HW_events_generator(float(row["median_daily_dhw_vol"]), seed, False)
			HWtestevents = HWtest.build_annual_HW_events()
			for event in HWtestevents:
				if event["type"].find("shower")!=-1:
					#5.901 is the implied average flowrate of HOT water in the sample data
					#this is not the same as the flowrate of a shower, whihch is of mixed warm water
					testvol[seed] += float(event["dur"]) * 5.901 / 365
				else:
					testvol[seed] += float(event["vol"]) / 365
		print(row["median_daily_dhw_vol"] + ",       " + str(statistics.mean(testvol)) + ",  " + str(statistics.variance(testvol)))
		row["calibration_daily_dhw_vol"] = statistics.mean(testvol)
		row["calibration_DHW_variance"] = statistics.variance(testvol)
		updated_rows.append(row)

headers = row.keys()

with open(decilebandingfile,'w', newline = '') as bandsfile:
	bandsfilewriter = csv.DictWriter(bandsfile, fieldnames = headers)
	bandsfilewriter.writeheader()
	for row in updated_rows:
		bandsfilewriter.writerow(row)
