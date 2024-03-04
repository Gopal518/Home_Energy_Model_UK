#!/usr/bin/env python3

"""
This module provides object(s) to represent ductwork
"""

# Standard library imports
import sys
from math import pi, log

# Set default value for the heat transfer coefficient inside the duct, in W / m^2 K 
INTERNAL_HTC = 15.5 # CIBSE Guide C, Table 3.25, air flow rate approx 3 m/s

# Set default values for the heat transfer coefficient at the outer surface, in W / m^2 K
EXTERNAL_REFLECTIVE_HTC = 5.7 # low emissivity reflective surface, CIBSE Guide C, Table 3.25
EXTERNAL_NONREFLECTIVE_HTC = 10.0 # high emissivity non-reflective surface, CIBSE Guide C, Table 3.25

class Ductwork:
    """ An object to represent ductwork for mechanical ventilation with heat recovery 
    (MVHR), assuming steady state heat transfer in a hollow cyclinder (duct)
    with radial heat flow. ISO 12241:2022 """

    def __init__(self, internal_diameter, external_diameter, length_in, length_out, k_insulation, thickness_insulation, reflective, MVHR_location):
        """Construct a ductwork object
        Arguments:
        internal_diameter    -- internal diameter of the duct, in m
        external_diameter    -- external diameter of the duct, in m
        length_in            -- length of intake duct, in m
        length_out           -- length of exhaust duct, in m
        k_insulation         -- thermal conductivity of the insulation, in W / m K
        thickness_insulation -- thickness of the duct insulation, in m
        reflective           -- whether the outer surface of the duct is reflective (true) or not (false) (boolean input)
        MVHR_location        -- location of the MVHR unit (inside or outside the thermal envelope) 
        """
        self.__length_in = length_in
        self.__length_out = length_out
        self.__MVHR_location = MVHR_location 

        """ Select the correct heat transfer coefficient for the outer surface, in W / m^2 K """
        if reflective:
            external_htc = EXTERNAL_REFLECTIVE_HTC
        else:
            external_htc = EXTERNAL_NONREFLECTIVE_HTC

        """ Calculate the diameter of the duct including the insulation (D_ins), in m"""
        self.__D_ins = external_diameter + (2.0 * thickness_insulation)

        """ Calculate the interior linear surface resistance, in K m / W  """
        self.__internal_surface_resistance = 1.0 / (INTERNAL_HTC * pi * internal_diameter)

        """ Calculate the insulation linear thermal resistance, in K m / W  """
        self.__insulation_resistance = log(self.__D_ins / internal_diameter) / (2.0 * pi * k_insulation)

        """ Calculate the exterior linear surface resistance, in K m / W  """
        self.__external_surface_resistance = 1.0 / (external_htc * pi * self.__D_ins)

    def get_MVHR_location(self):
        return self.__MVHR_location

    def duct_heat_loss(self, inside_temp, outside_temp, length):
        """" Return the heat loss for air inside the duct for the current timestep
        Arguments:
        inside_temp    -- temperature of air inside the duct, in degrees C
        outside_temp   -- temperature outside the duct, in degrees C
        """
        # Calculate total thermal resistance
        total_resistance = self.__internal_surface_resistance + self.__insulation_resistance + self.__external_surface_resistance

        # Calculate the heat loss, in W
        duct_heat_loss = (inside_temp - outside_temp) / (total_resistance) * length

        return duct_heat_loss

    def total_duct_heat_loss(self, outside_temp, supply_duct_temp, extract_duct_temp, intake_duct_temp, exhaust_duct_temp, efficiency):
        """" Return the heat loss for air inside the duct for the current timestep
        Arguments:
        outside_temp       -- temperature outside the duct, in degrees C
        supply_duct_temp   -- temperature of air inside the supply duct, in degrees C
        extract_duct_temp  -- temperature of air inside the extract duct, in degrees C
        intake_duct_temp   -- temperature of air inside the intake duct, in degrees C
        exhaust_duct_temp  -- temperature of air inside the exhaust duct, in degrees C
        efficiency         -- heat recovery efficiency of MVHR
        """
        # Outside location
        # Air inside the duct loses heat, external environment gains heat
        # Loses energy to outside in extract duct - losses must be X by the efficiency of heat recovery
        # Loses energy to outside in supply duct - lose all because after MVHR unit
        if self.__MVHR_location == 'outside':
            if supply_duct_temp is not None and extract_duct_temp is not None and intake_duct_temp is not None:
                outside_temp = intake_duct_temp
                supply_heat_loss = self.duct_heat_loss(supply_duct_temp, outside_temp, self.__length_in)
                extract_heat_loss = self.duct_heat_loss(extract_duct_temp, outside_temp,self.__length_out)
                total_duct_heat_loss = -(supply_heat_loss + (extract_heat_loss * efficiency))
            else:
                sys.exit('duct temperatures not provided for outside MVHR.')                

        # Inside location
        # This will be a negative heat loss i.e. air inside the duct gains heat, dwelling loses heat
        # Gains energy from zone in intake duct - benefit of gain must be X by the efficiency of heat recovery
        # Gains energy from zone in exhaust duct
        elif self.__MVHR_location == 'inside':
            if intake_duct_temp is not None and exhaust_duct_temp is not None and extract_duct_temp is not None:
                outside_temp = extract_duct_temp
                intake_heat_loss = self.duct_heat_loss(intake_duct_temp, outside_temp, self.__length_in)
                exhaust_heat_loss = self.duct_heat_loss(exhaust_duct_temp, outside_temp, self.__length_out)
                total_duct_heat_loss = (intake_heat_loss * efficiency) + exhaust_heat_loss
            else:
                sys.exit('duct temperatures not provided for inside MVHR.')
        else:
            sys.exit('MVHR location not valid.')
            # TODO Exit just the current case instead of whole program entirely?
            # TODO Add code to log an error

        return total_duct_heat_loss
