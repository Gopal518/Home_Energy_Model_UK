import csv
import sys
import os
import math
import random
import numpy as np
from functools import partial
from core.water_heat_demand.misc import frac_hot_water

class HW_event_adjust_allocate:
    '''
    class to determine HW events to be added to project dict
    based on showers, baths, other facilities present in dwelling
    '''
    def __init__(self, 
                 project_dict,
                 FHW,
                 event_temperature, 
                 HW_temperature, 
                 cold_water_feed_temps,
                 partGbonus):
        self.showers = []
        self.baths = []
        self.other= []
        self.which_shower = -1
        self.which_bath = -1
        self.which_other = -1
        self.event_temperature = event_temperature
        self.HW_temperature = HW_temperature
        self.cold_water_feed_temps = cold_water_feed_temps
        
        #utility for applying the sap10.2 monly factors (below)
        self.month_hour_starts = [744, 1416, 2160, 2880, 3624, 4344, 5088, 5832, 6552, 7296, 8016, 8760]
        #from sap10.2 J5
        self.behavioural_hw_factorm = [1.035, 1.021, 1.007, 0.993, 0.979, 0.965, 0.965, 0.979, 0.993, 1.007, 1.021, 1.035]
        #from sap10.2 j2
        self.other_hw_factorm = [1.10, 1.06, 1.02, 0.98, 0.94, 0.90, 0.90, 0.94, 0.98, 1.02, 1.06, 1.10, 1.00]
        
        #event and monthidx are only things that should change between events, rest are globals so dont need to be captured
        #we need unused "event" in shower and bath syntax so that its the same for all 3
        def showerdurationfunc (event):
            monthidx  = next(idx for idx, value in enumerate(self.month_hour_starts) if value > event["time"])
            return event["dur"] * FHW * self.behavioural_hw_factorm[monthidx]
        def bathdurationfunc (bathsize, flowrate, event):
            monthidx  = next(idx for idx, value in enumerate(self.month_hour_starts) if value > event["time"])
            #bathsize is already a volume of warm water (not hot water) 
            #so application frac_HW is unnecessary here
            return (bathsize / flowrate) * FHW * self.behavioural_hw_factorm[monthidx]
        def otherdurationfunc (flowrate, event):
            monthidx  = next(idx for idx, value in enumerate(self.month_hour_starts) if value > event["time"])
            frac_HW = frac_hot_water(event_temperature, HW_temperature, cold_water_feed_temps[math.floor(event["time"])])
            return (event["vol"] / frac_HW / flowrate) * FHW * self.other_hw_factorm[monthidx] * partGbonus
        '''
        set up events dict
        check if showers/baths are present
        if multiple showers/baths are present, we need to cycle through them
        if either is missing replace with the one that is present,
        if neither is present, "other" events with same consumption as a bath should be used
        '''
        project_dict["Events"].clear()
        project_dict["Events"]["Shower"] = {}
        project_dict["Events"]["Bath"] = {}
        project_dict["Events"]["Other"] = {}
        
        for shower in project_dict["Shower"]:
            project_dict["Events"]["Shower"][shower] = []
            self.showers.append(("Shower",shower,showerdurationfunc))
            
        for bath in project_dict["Bath"]:
            project_dict["Events"]["Bath"][bath] = []
            #partial bindings here allow these functions
            #to be used interchangeably, with event as the only argument
            self.baths.append(("Bath", bath, partial(bathdurationfunc, project_dict["Bath"][bath]["size"], project_dict["Bath"][bath]["flowrate"])))
            
        for other in project_dict["Other"]:
            project_dict["Events"]["Other"][other] = []
            self.other.append(("Other", other, partial(otherdurationfunc, project_dict["Other"][other]["flowrate"])))
        
        #if there are no other events we need to add them
        #using a default of 8.0l/min flowrate - 
        #event duration is calculated such as to deliver a fixed volume of water (otherdurationfunc above)
        #so this choice only affects how sharp peaks in HW demand can be.
        if self.other == []:
            if "header tank" in project_dict["ColdWaterSource"]:
                feedtype="header tank"
            else:
                feedtype="mains water"
            
            project_dict["Other"].update({        
                "other": {
            "flowrate": 8.0,
            "ColdWaterSource": feedtype
            }})
            project_dict["Events"]["Other"] = {"other":[]}
            self.other.append(("Other","other",partial(otherdurationfunc, project_dict["Other"]["other"]["flowrate"])))
        
        #if no shower present, baths should be taken and vice versa. 
        #If neither is present then bath sized drawoff
        if not self.showers and self.baths:
            self.showers = self.baths
        elif not self.baths and self.showers:
            self.baths = self.showers
        elif not self.showers and not self.baths:
            #bath sized events occur whenever a shower or bath would 
            #if there are no shower or bath facilities in the dwelling 
            #using a default of 100L and 8.0l/min flowrate
            self.baths.append(("Other","other",partial(bathdurationfunc, 100, 8.0)))
            self.showers.append(("Other","other",partial(bathdurationfunc, 100, 8.0)))
    '''
    the functions below return the name of the end user for the drawoff, 
    and the function to be used to calculate the duration of the drawoff.
    If there is no shower then baths are taken when showers would have been, as specified above, so
    this will return the duration function *for a bath* despite the event being named a shower.
    '''
    def get_shower(self):
        self.which_shower = (self.which_shower + 1) % len(self.showers)
        return self.showers[self.which_shower]
    def get_bath(self):
        self.which_bath = (self.which_bath + 1) % len(self.baths)
        return self.baths[self.which_bath]
    def get_other(self):
        self.which_other = (self.which_other + 1) % len(self.other)
        return self.other[self.which_other]
    
class HW_events_generator:
    
    def __init__(self, daily_DHW_vol, HWseed = 37, correct_banding = True):
        
        
        self.HWseed = HWseed
        self.rng = random.Random(self.HWseed)
        self.rng_poisson = np.random.default_rng(seed = self.HWseed)
        self.decile = -1
        self.banding_correction = 1.0
        
        self.target_DHW_vol = daily_DHW_vol
        
        this_directory = os.path.dirname(os.path.relpath(__file__))
        decilebandingfile =  os.path.join(this_directory, "decile_banding.csv")
        decileeventsfile =  os.path.join(this_directory, "day_of_week_events_by_decile.csv")
        decileeventtimesfile =  os.path.join(this_directory, "day_of_week_events_by_decile_event_times.csv")
        
        with open(decilebandingfile,'r') as bandsfile:
            bandsfilereader = csv.DictReader(bandsfile)
            bandsfiledata = []
            for row in bandsfilereader:
                bandsfiledata.append(row)
                if daily_DHW_vol >= float(row["min_daily_dhw_vol"])\
                    and daily_DHW_vol < float(row["max_daily_dhw_vol"]):
                    self.decile = int(row["decile"]) - 1
                    self.banding_correction = daily_DHW_vol / float(row["calibration_daily_dhw_vol"])
            if self.decile == -1:
                if daily_DHW_vol < float(bandsfiledata[0]["min_daily_dhw_vol"]):
                    self.decile = 0
                    self.banding_correction = daily_DHW_vol / float(row["calibration_daily_dhw_vol"])
                elif daily_DHW_vol > float(bandsfiledata[9]["min_daily_dhw_vol"]):
                    self.decile = 9
                    self.banding_correction = daily_DHW_vol / float(row["calibration_daily_dhw_vol"])
            if self.decile == -1:
                print("HW decile error, exiting")
                sys.exit()
        if not correct_banding:
            self.banding_correction = 1.0

        self.week = {
            'Monday':{},
            'Tuesday':{},
            'Wednesday':{},
            'Thursday':{},
            'Friday':{},
            'Saturday':{},
            'Sunday':{},
        }

        with open(decileeventsfile,'r') as varsfile:
            varsfilereader = csv.DictReader(varsfile)
            for i, row in enumerate(varsfilereader):
                if int(row["decile"]) - 1 ==  self.decile:
                    self.week[row['day_name']].update(
                        {row["simple_labels2_based_on_900k_sample"]:{
                            "event_count": float(row["event_count"]),
                            "median_event_volume":float(row["median_event_volume"]),
                            "mean_event_volume":float(row["mean_event_volume"]),
                            "median_dur":float(row["median_dur"]) / 60,
                            "mean_dur":float(row["mean_dur"]) / 60, # convert units to minutes
                            "hourly_event_counts" : [0 for x in range(24)]
                            }
                        }
                    )

        with open(decileeventtimesfile,'r') as varsfile:
            varsfilereader = csv.DictReader(varsfile)
            for i, row in enumerate(varsfilereader):
                self.week[row["day_name"]]\
                    [row["simple_labels2_based_on_900k_sample"]]\
                    ["hourly_event_counts"]\
                    [int(row["hour"])] = int(row["event_count"])

        for day in self.week:
            for event_type in self.week[day]:
                hrlyeventcnts = self.week[day][event_type]['hourly_event_counts']
                sumeventcnt = sum(hrlyeventcnts)
                '''
                sucessive calls to a poisson distribution with fixed seed 
                will yield the same answer - have to ask rng to generate an 
                array of poisson samples and draw from it.
                generate array of size 53 as each hour is unique per week of the year
                
                '''
                self.week[day][event_type].update\
                (
                    {'hourly_event_distribution':\
                     [{"poisson_arr":self.rng_poisson.poisson(self.banding_correction *\
                     x * float(self.week[day][event_type]['event_count'])/ sumeventcnt,53).tolist(),\
                     '__poisson_arr_idx':0}
                    for x in hrlyeventcnts]}
                )
        

    def events_in_hour(self, time, type, event_dict):
        out = []
        count = event_dict['hourly_event_distribution'][math.floor(time % 24)]["poisson_arr"]\
                [event_dict['hourly_event_distribution'][math.floor(time % 24)]['__poisson_arr_idx']]
        event_dict['hourly_event_distribution'][math.floor(time % 24)]['__poisson_arr_idx'] += 1
        for i in range(count):
            out.append({
                'time': time + self.rng.random(), #random offset to time within the hour
                'type': type,
                'vol': event_dict["mean_event_volume"], #these could be distributed rather than always the mean
                'dur': event_dict["mean_dur"]
            })
        return out
    
    def overlap_check(self,hrlyevents, matchingtypes, eventstart, duration):
        for existing_event in hrlyevents[math.floor(eventstart)]:
            if (existing_event["type"] in matchingtypes)\
             and ((eventstart >= existing_event["eventstart"]\
                   and eventstart < existing_event["eventend"])\
                   or (eventstart + duration / 60 >= existing_event["eventstart"]\
                   and eventstart + duration / 60 < existing_event["eventend"])):
                #events are overlapping and we need to reroll the time until they arent.
                eventstart = self.reroll_event_time(eventstart)
                self.overlap_check(hrlyevents,matchingtypes, eventstart, duration)
    
    def reroll_event_time(self, time):
        #sometimes events will overlap and we need to change the time so they dont
        #do this by adding random value betwen 0-30 mins to current time until its not overlapping with anything
        return (time + self.rng.random() / 2) % 8760
    
    def build_annual_HW_events(self, startday = 0):
        list_days = list(zip(*list(self.week.items())))[1]
        annual_HW_events = []
        for day in range(365):
            for hour in range(24):
                for event_type in list_days[(day + startday) % 7]:
                    annual_HW_events.extend(self.events_in_hour(hour + (day * 24), event_type, list_days[day % 7][event_type]))
        return annual_HW_events
                    