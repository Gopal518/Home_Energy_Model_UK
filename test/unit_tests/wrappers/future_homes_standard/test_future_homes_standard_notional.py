#!/usr/bin/env python3

"""
This module contains unit tests for the notional building
"""

# Standard library imports
import unittest
import json
import os
from copy import deepcopy

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.space_heat_demand.building_element import HeatFlowDirection
from wrappers.future_homes_standard.future_homes_standard import calc_TFA
from wrappers.future_homes_standard import future_homes_standard_notional



class NotionalBuildingHeatPump(unittest.TestCase):
	""" Unit tests for Notional Building """

	def setUp(self):
		this_directory = os.path.dirname(os.path.relpath(__file__))
		file_path =  os.path.join(this_directory, "test_future_homes_standard_notional_input_data.json")
		with open(file_path) as json_file:
			self.project_dict = json.load(json_file)
		# Determine cold water source
		cold_water_type = list(self.project_dict['ColdWaterSource'].keys())
		if len(cold_water_type) == 1:
			self.cold_water_source = cold_water_type[0]
		else:
			sys.exit('Error: There should be exactly one cold water type')

		# Defaults
		self.hw_timer = "hw timer"
		self.hw_timer_eco7 = "hw timer eco7"
		self.notional_HP = 'notional_HP'
		self.is_notA = True
		self.is_FEE  = False
		self.energysupplyname_main = 'mains elec' 
		self.TFA = calc_TFA(self.project_dict)
		self.opening_lst = ['open_chimneys', 'open_flues', 'closed_fire', 'flues_d', 'flues_e',
						'blocked_chimneys', 'passive_vents', 'gas_fires']
		self.table_R2 = {
			'E1' : 0.05,
			'E2' : 0.05,
			'E3' : 0.05,
			'E4' : 0.05,
			'E5' : 0.16,
			'E19' : 0.07,
			'E20' : 0.32,
			'E21' : 0.32,
			'E22' : 0.07,
			'E6' : 0,
			'E7' : 0.07,
			'E8' : 0,
			'E9' : 0.02,
			'E23' : 0.02,
			'E10' : 0.06,
			'E24' : 0.24,
			'E11' : 0.04,
			'E12' : 0.06,
			'E13' : 0.08,
			'E14' : 0.08,
			'E15' : 0.56,
			'E16' : 0.09,
			'E17' : -0.09,
			'E18' : 0.06,
			'E25' : 0.06,
			'P1' : 0.08,
			'P6' : 0.07,
			'P2' : 0,
			'P3' : 0,
			'P7' : 0.16,
			'P8' : 0.24,
			'P4' : 0.12,
			'P5' : 0.08 ,
			'R1' : 0.08,
			'R2' : 0.06,
			'R3' : 0.08,
			'R4' : 0.08,
			'R5' : 0.04,
			'R6' : 0.06,
			'R7' : 0.04,
			'R8' : 0.06,
			'R9' : 0.04,
			'R10' : 0.08,
			'R11' : 0.08
			}

	def test_edit_lighting_efficacy(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_lighting_efficacy(project_dict)

		for zone in project_dict['Zone'].values():
			self.assertTrue("Lighting" in zone)
			self.assertEqual(zone["Lighting"]["efficacy"], 120)

	def test_edit_infiltration(self):

		project_dict = deepcopy(self.project_dict)
		is_notA = False
		future_homes_standard_notional.edit_infiltration(project_dict, is_notA)
		self.assertEqual(project_dict["Infiltration"]["test_type"], "50Pa")
		self.assertEqual(project_dict["Infiltration"]["test_result"], 2.5)

		self.assertTrue("NumberOfWetRooms" in project_dict)
		wet_rooms_count = project_dict["NumberOfWetRooms"]
		self.assertTrue(wet_rooms_count > 1)
		self.assertTrue("extract_fans" in project_dict["Infiltration"])
		self.assertEqual(project_dict["Infiltration"]["extract_fans"], 2)

		project_dict = deepcopy(self.project_dict)
		is_notA = True
		future_homes_standard_notional.edit_infiltration(project_dict, is_notA)
		self.assertEqual(project_dict["Infiltration"]["test_type"], "50Pa")
		self.assertEqual(project_dict["Infiltration"]["test_result"], 2)

		for opening in self.opening_lst:
			self.assertEqual(project_dict["Infiltration"][opening], 0)

		self.assertTrue("NumberOfWetRooms" in project_dict)
		wet_rooms_count = project_dict["NumberOfWetRooms"]
		self.assertTrue(wet_rooms_count > 1)
		self.assertTrue("extract_fans" in project_dict["Infiltration"])
		self.assertEqual(project_dict["Infiltration"]["extract_fans"], 0)

	def test_edit_opaque_ajdZTU_elements(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_opaque_ajdZTU_elements(project_dict)

		for zone in project_dict["Zone"].values():
			for building_element in zone["BuildingElement"].values():
				if building_element["pitch"] == HeatFlowDirection.DOWNWARDS:
					self.assertEqual(building_element["u_value"], 0.13)
				elif building_element["pitch"] == HeatFlowDirection.UPWARDS:
					self.assertEqual(building_element["u_value"], 0.11)
				elif building_element["pitch"] == HeatFlowDirection.HORIZONTAL:
					if "is_external_door" in building_element:
						if building_element["is_external_door"]:
							self.assertEqual(building_element["u_value"], 1.0)
						else:
							self.assertEqual(building_element["u_value"], 0.18)
					else:
						self.assertEqual(building_element["u_value"], 0.18)

	def test_edit_ground_floors(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_ground_floors(project_dict)

		for zone in project_dict["Zone"].values():
			for building_element in zone["BuildingElement"].values():
				if building_element["type"] == "BuildingElementGround":
					self.assertEqual(building_element["u_value"], 0.13)
					self.assertEqual(building_element["r_f"], 6.12)
					self.assertEqual(building_element["psi_wall_floor_junc"], 0.16)

	def test_edit_thermal_bridging(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_thermal_bridging(project_dict)

		for zone in project_dict["Zone"].values():
			if "ThermalBridging" in zone:
				for thermal_bridge in zone["ThermalBridging"].values():
					if thermal_bridge["type"] == "ThermalBridgePoint":
						self.assertEqual(thermal_bridge["heat_transfer_coeff"], 0.0)
					elif thermal_bridge["type"] == "ThermalBridgeLinear":
						junction_type = thermal_bridge["junction_type"]
						self.assertTrue(junction_type in self.table_R2) 
						self.assertEqual(
							thermal_bridge["linear_thermal_transmittance"],
							self.table_R2[junction_type],
						)

	def test_calc_max_glazing_area_fraction(self):
		project_dict = {
			"Zone": {
				"test_zone": {
					"BuildingElement": {
						"test_rooflight": {
							"type": "BuildingElementTransparent",
							"pitch": 0.0,
							"height": 2.0,
							"width": 1.0,
							}
						}
					}
				}
			}

		project_dict["Zone"]["test_zone"]["BuildingElement"]["test_rooflight"]["u_value"] = 1.5
		self.assertEqual(
			future_homes_standard_notional.calc_max_glazing_area_fraction(project_dict, 80.0),
			0.24375,
			"incorrect max glazing area fraction",
			)

		project_dict["Zone"]["test_zone"]["BuildingElement"]["test_rooflight"]["u_value"] = 1.0
		self.assertEqual(
			future_homes_standard_notional.calc_max_glazing_area_fraction(project_dict, 80.0),
			0.25,
			"incorrect max glazing area fraction",
			)

		project_dict["Zone"]["test_zone"]["BuildingElement"]["test_rooflight"]["u_value"] = 1.5
		project_dict["Zone"]["test_zone"]["BuildingElement"]["test_rooflight"]["pitch"] = 90.0
		self.assertEqual(
			future_homes_standard_notional.calc_max_glazing_area_fraction(project_dict, 80.0),
			0.25,
			"incorrect max glazing area fraction when there are no rooflights",
			)

	def test_edit_bath_shower_other(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_bath_shower_other(project_dict, self.cold_water_source)

		expected_bath = {
			"medium": {
				"ColdWaterSource": self.cold_water_source,
				"flowrate": 12,
				"size": 73
			}
		}

		expected_shower = {
			"mixer": {
				"ColdWaterSource": self.cold_water_source,
				"flowrate": 8,
				"type": "MixerShower"
			}
		}

		expected_other = {
			"other": {
				"ColdWaterSource": self.cold_water_source,
				"flowrate": 6
			}
		}

		self.assertDictEqual(project_dict['Bath'], expected_bath)
		self.assertDictEqual(project_dict['Shower'], expected_shower)
		self.assertDictEqual(project_dict['Other'], expected_other)

	def test_add_wwhrs(self):
		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.add_wwhrs(project_dict, self.cold_water_source, self.is_notA, self.is_FEE)

		expected_wwhrs = {
			"Notional_Inst_WWHRS": {
				"ColdWaterSource": self.cold_water_source,
				"efficiencies": [50, 50],
				"flow_rates": [0, 100],
				"type": "WWHRS_InstantaneousSystemB",
				"utilisation_factor": 0.98
			}
		}

		if project_dict['Infiltration']['storeys_in_building'] > 1 and self.is_notA and not self.is_FEE:
			self.assertIn("WWHRS", project_dict)
			self.assertDictEqual(project_dict['WWHRS'], expected_wwhrs)
			self.assertEqual(project_dict['Shower']['mixer']["WWHRS"], "Notional_Inst_WWHRS")
		else:
			self.assertNotIn("WWHRS", project_dict)
			self.assertNotIn("WWHRS", project_dict['Shower']['mixer'])

	def test_calculate_daily_losses(self):
		expected_cylinder_vol = 265
		daily_losses = future_homes_standard_notional.calculate_daily_losses(expected_cylinder_vol)
		expected_daily_losses = 1.03685  

		self.assertAlmostEqual(daily_losses, expected_daily_losses, places=5)

	def test_edit_storagetank(self):
		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_storagetank(project_dict, self.cold_water_source, self.TFA)
		expected_primary_pipework_dict = {
			"internal_diameter_mm": 25,
			"external_diameter_mm": 27,
			"length": 2.0,
			"insulation_thermal_conductivity": 0.035,
			"insulation_thickness_mm": 25,
			"surface_reflectivity": False,
			"pipe_contents": "water"
		}

		expected_hotwater_source = {
			'hw cylinder': {
				'ColdWaterSource': self.cold_water_source,
				'HeatSource': {
					self.notional_HP: {
						'ColdWaterSource': self.cold_water_source,
						'EnergySupply': self.energysupplyname_main,
						'heater_position': 0.1,
						'name': self.notional_HP,
						'temp_flow_limit_upper': 60,
						'thermostat_position': 0.1,
						'type': 'HeatSourceWet'
					}
				},
				'daily_losses': 0.46660029577109363, 
				'type': 'StorageTank',
				'volume': 80.0,
				'primary_pipework': expected_primary_pipework_dict,
			}
		}
		self.assertDictEqual(project_dict['HotWaterSource'], expected_hotwater_source)

	def test_calc_daily_hw_demand(self):
		project_dict = deepcopy(self.project_dict)
		cold_water_source_name = list(project_dict['ColdWaterSource'].keys())[0]

		# Add notional objects that affect HW demand calc
		future_homes_standard_notional.edit_bath_shower_other(project_dict, cold_water_source_name)

		daily_HWD = future_homes_standard_notional.calc_daily_hw_demand(
			project_dict,
			self.TFA,
			cold_water_source_name,
			)
		expected_result = [
			5.332358870360489, 5.939519167409699, 4.092522651160197, 11.125709204618492, 2.683734986543989,
			9.383926198021308, 7.276644602132959, 9.905550232417198, 5.868348111624264, 5.000004314682442,
			9.102840819741823, 4.234526304946405, 11.100186816381557, 15.348824847273903, 9.246285943546356,
			6.5696948007576434, 11.1612061494084, 10.733958619860395, 7.791532848311438, 6.627265970392273,
			5.96606164905874, 3.618690579010297, 5.097644689351863, 7.905654183398964, 3.5911429248554914,
			6.931386421275378, 3.9821383566541404, 4.3033711847540035, 13.556004119647904, 9.954514852596839,
			6.964478582194271, 4.734046394182493, 8.649179975112212, 5.25478413888494, 3.9530611705058227,
			6.283086643171573, 6.406706699161304, 5.606989680610464, 12.468376402873018, 5.419626263745942,
			5.872152585988534, 7.429943144307275, 3.8932783845394705, 5.606267945072289, 9.65440986957507,
			6.890177600713714, 4.845355757781505, 9.193220976778155, 5.655617973289041, 6.064895583458154,
			7.244053287963995, 6.269171253951853, 3.017063334618479, 14.935951183776739, 12.94660499419203,
			9.207290605900793, 10.064548272991349, 6.357349410695312, 4.988309743710779, 5.944119882202128,
			5.484461140494693, 15.177903714441321, 7.4169541627030595, 6.053285706116112, 7.249558004142308,
			4.046916402279789, 5.721069409428999, 4.056253121219603, 3.8410601558871202, 7.441963364046647,
			5.211078637540669, 3.594949370189899, 8.582498633450516, 12.520468311045741, 3.182405750163948,
			8.549383500720023, 8.484923528552315, 6.11991505631395, 11.264431683507613, 7.968546208361992,
			4.891724308327831, 8.878345140054341, 5.897584047536178, 10.1082495590307, 4.901851444485903,
			4.474580986555416, 5.048224350533313, 4.678526095553983, 6.702824355759434, 1.9932691952303097,
			11.309874044799988, 8.909469281155683, 4.232998459222833, 6.9549019272738475, 2.899788163834349,
			11.335766800758424, 9.83674039550925, 5.272144007862989, 6.261738757123254, 7.601760156441395,
			5.204361575580094, 4.619565231848526, 6.176137776056494, 5.514045731129771, 3.1366923956877186,
			10.630811892389696, 3.542033417123719, 5.410401859498289, 6.519151906355308, 6.019958035401171,
			6.243292125689517, 9.084965214352255, 2.7428629227499153, 2.1752807626132418, 5.6836654164665825,
			6.628277939182285, 6.341991586154915, 6.440185068183707, 6.576397433157791, 10.78952628021809,
			5.048102876562236, 3.6386977195991745, 7.648896063912615, 4.781780460377417, 3.095000623305923,
			4.46257059778781, 10.329596970282955, 6.942969560891599, 6.318260467422231, 13.433436450614568,
			5.926103248090028, 3.6064719273950407, 4.867494151718431, 6.17627162034108, 3.4840860111547816,
			3.4788248811311133, 3.6075680564251598, 3.1708644065257845, 5.140059056069278, 11.377969510009006,
			9.88361662129783, 2.412095962863254, 8.039098871530262, 4.513498906513583, 8.39182153549336,
			5.237748680991073, 7.710727087549717, 5.545313188367929, 3.2614142620635564, 8.15102417032649,
			6.113786765235915, 3.0462008728724186, 4.627644745707857, 8.96760363640186, 7.869720648636622,
			2.5572171241264674, 7.772911678408069, 4.5205213857079505, 4.7241011656160286, 4.31583260334098,
			8.392297126697175, 3.0390045323633097, 2.561758635743069, 3.8055121960102465, 4.957770707010701,
			7.676816787247491, 2.407241282557557, 10.288106047693773, 5.3664644008984395, 9.688582162151178,
			6.2758152163561824, 3.426156337911544, 4.605934996360963, 6.920271447213809, 6.671093970146627,
			4.463070793041712, 8.134076860487129, 7.464564386260888, 3.184254920801133, 7.6831295559993285,
			3.1992792494123745, 2.8910535510553643, 6.221241585813495, 6.033380220879017, 7.734043467487455,
			2.8823504901399866, 7.09612065230572, 6.0253402880463085, 3.50287184242603, 3.500113166159563,
			4.8838421894295205, 5.568459031472862, 5.801671459276577, 7.318062945413172, 4.560137196453809,
			5.952778364534861, 4.263543713756446, 6.097632784863535, 4.696865417816497, 3.7740902405565064,
			5.16877248875722, 5.162480044689767, 3.480470677115114, 7.75192694081488, 4.101755187715797,
			7.381443272701809, 4.098841464734976, 3.1993564276889224, 5.040792088177463, 4.513083734241988,
			6.317681344440151, 2.7439044812169926, 5.898142422154367, 7.371060672897773, 7.9382069864356595,
			3.5265885568978854, 7.728561460772754, 6.90935469115776, 4.430635427013582, 8.170763380469982,
			6.132657970862075, 4.631615784693746, 6.264405801911571, 6.464844354983229, 4.266327548130808,
			5.963112907970409, 6.933072249037472, 4.229825026146224, 4.013862525963428, 9.039362396709436,
			7.285707935765941, 8.968099095377662, 4.341081900663293, 6.917518202342683, 5.164935282976035,
			2.530324124620448, 5.393220314414821, 5.189402505814991, 5.574963098297244, 5.598838783559906,
			3.1739305639235624, 4.460613099897497, 3.627833706011235, 10.003466367606544, 2.975228012155293,
			8.150670425984215, 5.12934624417735, 4.324060208032451, 4.927430673530184, 4.221873521091226,
			2.9607093976509526, 3.010109340930027, 3.8080504716951387, 5.334896616074902, 3.6586567562894654,
			6.271402247498758, 7.0782813369230455, 2.342073386651291, 3.144078875386038, 3.44667994569649,
			6.298084449774622, 3.3299572531554333, 6.949389429005877, 7.263536771162239, 6.072254433289421,
			3.8155899819551684, 4.790116413410102, 5.655326040499874, 2.4737002270904354, 3.780632006228946,
			4.3535064060269955, 4.201068552779499, 7.761334516016323, 7.5540577560987385, 8.083786382102824,
			10.846122101158743, 4.142063737640603, 6.267918299159879, 4.433010039599949, 3.8922385480764823,
			7.922987532593388, 5.394915277228311, 8.128547962099702, 3.2364949656999573, 8.236112522045971,
			2.9501733840944353, 5.095266550325053, 6.1431501896601235, 6.950637135573592, 4.171005399737451,
			9.35599615925421, 2.899378069279008, 4.8121788692676715, 6.570167885003649, 2.565849518392064,
			4.7137771160765345, 5.088347786050735, 6.463968407009868, 5.968097693153073, 14.438774178973642,
			4.637304612995721, 5.275561066357465, 7.551761898546344, 2.1214983279627213, 6.470868818895256,
			6.474595656576856, 8.024048638394715, 12.889956558433163, 8.95785021997712, 5.419468841823875,
			4.414912376452211, 8.40783283608238, 3.104171170052293, 7.360305184226255, 14.139815632055676,
			8.789288381510925, 5.952974166665065, 4.078494012824973, 5.080258668518449, 4.488561133836422,
			4.764103823990652, 5.798522605564636, 10.74911588213892, 5.022580729207448, 6.324466421123345,
			3.988806746396135, 6.840653301262988, 9.825079826042588, 6.040742518638523, 6.0589415306794905,
			3.094885568167805, 6.660422855536369, 6.611471757465271, 3.0122910773699885, 4.9934335234921035,
			5.07034302912691, 5.996529254492781, 6.437875615060707, 5.558383928156852, 8.582394315779466,
			4.863603644428352, 5.939084411607102, 8.581974300855885, 6.755878513731192, 11.238662560978797,
			13.585318787745397, 4.936075532249035, 13.50298793032555, 4.89919471806078, 6.070030937282697,
			6.909639092531857, 4.455395447933453, 6.184649184662782, 6.48039956980252, 7.013290350460273,
			7.1824282981170295, 4.5042825166870415, 11.882961146036742, 8.294905919665387, 5.566468234301784,
			9.054801851625005, 9.033821895974768, 4.876234403795807, 6.3055737634345315, 6.904816967680408]
		self.assertEqual(daily_HWD, expected_result, "incorrect daily hot water demand calculated")

	def test_edit_hot_water_distribution_inner(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_hot_water_distribution_inner(project_dict, self.TFA)

		expected_hot_water_distribution_inner_dict = {
			"external_diameter_mm": 27,
			"insulation_thermal_conductivity": 0.035,
			"insulation_thickness_mm": 38, 
			"internal_diameter_mm": 25, 
			"length": 8.0,
			"pipe_contents": "water",
			"surface_reflectivity": False
		}

		self.assertDictEqual(project_dict['Distribution']['internal'], expected_hot_water_distribution_inner_dict)

	def test_edit_spacecoolsystem(self):

		project_dict = deepcopy(self.project_dict)
		project_dict['PartO_active_cooling_required'] = True

		future_homes_standard_notional.edit_spacecoolsystem(project_dict)

		for space_cooling_name, system in project_dict['SpaceCoolSystem'].items():
			self.assertEqual(system['efficiency'], 5.1)
			self.assertEqual(system['frac_convective'], 0.95)


	def test_add_solar_PV_house_only(self):

		project_dict = deepcopy(self.project_dict)
		expected_result = {'PV1': {
					'EnergySupply': 'mains elec',
					'orientation360': 180, 
					'peak_power': 4.444444444444445,
					'pitch': 45,
					'type': 'PhotovoltaicSystem', 
					'ventilation_strategy': 'moderately_ventilated',
					'base_height': 1,
					'width': 6.324555320336759,
					'height': 3.1622776601683795
					}
			}

		future_homes_standard_notional.add_solar_PV(project_dict, self.is_notA, self.is_FEE, self.TFA)

		self.assertDictEqual(project_dict['OnSiteGeneration'], expected_result)

