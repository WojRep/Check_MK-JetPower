#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
from .agent_based_api.v1 import *

from .agent_based_api.v1.type_defs import *

from .utils import (
    temperature,
)

from typing import Dict, List

from cmk.utils import debug
from pprint import pprint

###############################

UNIT = {
    "c": u"°C",
    "f": u"°F",
    "k": u"K",
    'v': u"V",
    'a': u"A",
    'w': u"W",
    'wh': u"Wh",
    'hz': u"Hz",
    'pa': u"Pa",
    '%': u"%",
    'ug/m3': u"µg/㎥",
}

def _render_template(value: float):
    template = "%%%s" % ("d" if isinstance(value, int) else ".1f")
    return template % value


def _render_func(value: float, unit: str) -> str:
    return _render_template(value) + UNIT.get(unit) if UNIT.get(unit) else ''


def _isFloat(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def _isInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


#####################################################
#####################################################
##                                                 ##
##      ___      _  ______                         ##
##     |_  |    | | | ___ \       CAS-02           ##
##       | | ___| |_| |_/ /____      _____ _ __    ##
##       | |/ _ \ __|  __/ _ \ \ /\ / / _ \ '__|   ##
##   /\__/ /  __/ |_| | | (_) \ V  V /  __/ |      ##
##   \____/ \___|\__\_|  \___/ \_/\_/ \___|_|      ##
##                                                 ##
##   Status                                        ##
##                                                 ##
#####################################################
#####################################################


SYSTEM_STATUS_NAME = {
	"1": "normal",
	"2": "minnor alarm",
        "3": "major alarm",
}

alarm_name = {
	"0": "normal",
	"1": "Alarm",
}

NAME="jetpower_cas02"
SNMP_BASE = ".1.3.6.1.4.1.38747.1"
SNMP_DETECT = startswith('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.38747') and startswith('.1.3.6.1.2.1.1.5.0', 'CAS-02')

OIDs = {
'0': {'id': 'model_name', 'oid': '2.0', 'name': "Model", 'do_metric': False, 'unit': None, },
'1': {'id': 'firmware_version', 'oid': '3.0', 'name': 'Firmware', 'do_metric': False, 'unit': None, },
'2': {'id': 'site_name', 'oid': '4.0', 'name': 'Site name', 'do_metric':False, 'unit': None, },
'3': {'id': 'system_status', 'oid': '5.0', 'name': 'System status', 'do_metric': True, 'unit':'', 'divider': 1,  },
'4': {'id': 'system_voltage', 'oid': '6.0', 'name': 'Voltage', 'do_metric': True, 'unit': 'v', 'divider': 1000, },
'5': {'id': 'system_current_load', 'oid': '7.0', 'name': 'Current load', 'do_metric': True, 'unit': 'a', 'divider': 1000, },
'6': {'id': 'system_ac', 'oid': '8.0', 'name': 'AC voltage', 'do_metric': True, 'unit': 'v',  'divider': 1000,  },
}


def parse_jetpower_cas02(string_table):
    param_list = {}
    parameters = string_table[0]
    for n in range(len(parameters)):
        name = OIDs[str(n)].get('name')
        do_metric = OIDs[str(n)].get('do_metric') if OIDs[str(n)].get('do_metric') else ''
        divider =  OIDs[str(n)].get('divider') if OIDs[str(n)].get('divider') else 1

        if _isInt(parameters[n]) and divider == 1:
            value = int(parameters[n])

        elif _isFloat(parameters[n]):
            value = float(int(parameters[n]) / divider)

        else:
            value = str(parameters[n])
            if (value is None) or (value == ''):
                value = chr(216)

        param_list.update(
		{str(OIDs[str(n)]['id']): {
		    'value': value,
		    'name': name,
		    'do_metric': do_metric,
		}})
    return param_list


def discover_jetpower_cas02(section):
#    if len(section) == 0:
#        return
    yield Service(item="JetPower Info")
    yield Service(item="JetPower Status")


def check_jetpower_cas02(item, params, section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data")
        return
    if item == "JetPower Info":
        model_name = section['model_name']['value']
        firmware_version = section['firmware_version']['value']
        site_name = section['site_name']['value']
        if (model_name == "CAS-02") and (firmware_version < 66):
            yield Result(state=State.CRIT, summary=f"Upgrade firmware !!! - Your firmware: {firmware_version}")
            return
        else:
            yield Result(state=State.OK, summary=f"Model: {model_name}, Firmware: {firmware_version}, Site name: {site_name}")
        return
    if item == "JetPower Status":
        system_status = section['system_status']['value']
        system_voltage = section['system_voltage']['value']
        system_current_load = section['system_current_load']['value']
        system_ac = section['system_ac']['value']
        system_voltage = float("{:.1f}".format(system_voltage))
        system_current_load = float("{:.2f}".format(system_current_load))
        system_ac = float("{:.2f}".format(system_ac))
        summary = f"Status: {SYSTEM_STATUS_NAME.get(str(system_status))}, AC: {system_ac}"
        summary = summary + f"V, Voltage: {system_voltage}V, Current load: {system_current_load}A."
        if system_status == 1:
            state=State.OK
        elif system_status == 2:
            state=State.WARN
        elif system_status == 3:
            state=State.CRIT
        else:
            state=State.UNKNOWN
        yield Result(state=state, summary=summary)
        yield Metric('system_status', system_status)
        yield Metric('system_voltage', system_voltage)
        yield Metric('system_current_load', system_current_load)
        yield Metric('system_ac', system_ac)
        return
    yield Result(state=State.UNKNOWN, summary="No item or data")
    return


register.snmp_section(
    name=NAME,
    fetch = SNMPTree(
        base = SNMP_BASE,
        oids = [ oid['oid'] for _, oid in OIDs.items()],
    ),
    detect = SNMP_DETECT,
    parse_function = parse_jetpower_cas02,
)


register.check_plugin(
    name = NAME,
    sections=[NAME],
    service_name = "%s",
    discovery_function = discover_jetpower_cas02,
    check_default_parameters={},
    check_ruleset_name=NAME,
    check_function = check_jetpower_cas02,
)

#####################################################
#####################################################
##                                                 ##
##      ___      _  ______                         ##
##     |_  |    | | | ___ \       CAS-02           ##
##       | | ___| |_| |_/ /____      _____ _ __    ##
##       | |/ _ \ __|  __/ _ \ \ /\ / / _ \ '__|   ##
##   /\__/ /  __/ |_| | | (_) \ V  V /  __/ |      ##
##   \____/ \___|\__\_|  \___/ \_/\_/ \___|_|      ##
##                                                 ##
##   Temperature                                   ##
##                                                 ##
#####################################################
#####################################################

ALARM = {
'0': 'Ambient temp. too HIGH',
'1': 'Ambient temp. too LOWER',
'2': 'Rectifiers PFC temp too HIGH',
'3': 'Rectifiers DC-DC temp too HIGH',
}


def discover_jetpower_cas02_temp(section):
    if (not section[0]) or (section[0] == None) or (section[0] == ""):
        return
    yield Service(item="JetPower Temp")


def check_jetpower_cas02_temp(item, params, section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data")
        return

    if item and section[0] :
        alarms=section[0]
        state=State.OK

        for n in range(len(alarms)):
            alarm_value = int(alarms[n])
            if alarm_value == 1:
                summary = ALARM.get(str(n))
                state = State.CRIT
                yield Result(state=state, summary=summary)

        if state == State.OK:
            summary = f'Temperature is OK.'
            yield Result(state=state, summary=summary)
        return

    else:
        yield Result(state = State.UNKNOWN, summary = "No correct data")

register.snmp_section(
    name=NAME + "_temp",
    fetch = SNMPTree(
	base = SNMP_BASE,
	oids = [
            "27.0", # Ambient Over temperature: 0 - normal, 1 - alarm
            "28.0", # Ambient Under temperature: 0 - normal, 1 - alarm
            "29.0", # Rectifiers PFC temperature: 0 - normal, 1 - alarm too hight
            "30.0", # Rectifiers DHDH temperature: 0 - normal, 1 - alarm too hight
	],
    ),
    detect = SNMP_DETECT,
)

register.check_plugin(
    name = NAME + "_temp",
    sections=[NAME+"_temp"],
    service_name = "%s",
    discovery_function = discover_jetpower_cas02_temp,
    check_default_parameters={},
    check_ruleset_name='',
    check_function = check_jetpower_cas02_temp,
)


#####################################################
#####################################################
##                                                 ##
##      ___      _  ______                         ##
##     |_  |    | | | ___ \       CAS-02           ##
##       | | ___| |_| |_/ /____      _____ _ __    ##
##       | |/ _ \ __|  __/ _ \ \ /\ / / _ \ '__|   ##
##   /\__/ /  __/ |_| | | (_) \ V  V /  __/ |      ##
##   \____/ \___|\__\_|  \___/ \_/\_/ \___|_|      ##
##                                                 ##
##   Batteries                                     ##
##                                                 ##
#####################################################
#####################################################

BATT_STATUS = {
	'1': { 'name': 'in float charge',	'status': State.OK, },
	'2': { 'name': 'in equal charge',	'status': State.OK, },
}

BATT_CURRENT_ALARM = {
	'0': { 'name': 'normal',	'status': State.OK, },
	'1': { 'name': 'too HIGH',	'status': State.WARN, },
}

BATT_TEMP_ALARM = {
	'0': { 'name': 'normal',	'status': State.OK, },
	'1': { 'name': 'ABNORMAL',	'state': State.CRIT, },
}

BATT_BLVD_ALARM = {
	'0': { 'name': 'normal',	'status': State.OK, },
	'1': { 'name': 'too LOW',	'state': State.CRIT, },
}

BATT_CB_ALARM = {
	'0': { 'name': 'OK', 	'status': State.OK, },
	'1': { 'name': 'BROKEN', 'status': State.CRIT, },
}

BATT_OIDs = [
    {'id': 'batt_number', 'name': 'Batt No', 'long_name': 'Battery number', 'oid': "9.0", 'do_metric': False, 'unit': None, 'result': True, },			# Battery number
    {'id': 'batt_soc', 'name': 'SoC', 'long_name': 'Battery Soc', 'oid': "10.0", 'do_metric': True,'unit': '%' ,'result': True, },
    {'id': 'batt_current', 'name': 'Load', 'long_name': 'Battery current','oid': "11.0",'do_metric': True,'unit': 'a', 'divider': 1000, 'result': True, },			# Battery current: <0 - discharge, >0 - charge battery
    {'id': 'batt_temp', 'name': 'Temp', 'long_name': 'Battery temperature','oid': "12.0",'do_metric': True,'unit': 'c', 'divider': 1000, 'result': True, },
    {'id': 'batt_charge_mode', 'name': 'Charge mode', 'long_name': 'Charge mode of battery','oid': "13.0",'do_metric': True,'unit': None, 'result': True, 'alarm': BATT_STATUS, },		# Status of battery work: 1 float, 2 - equal
    {'id': 'batt_current_alarm', 'name': 'Load status', 'long_name': 'Current of battery','oid': "40.0",'do_metric': False,'unit': None, 'result': True, 'alarm': BATT_CURRENT_ALARM, },		# whether the current of the battery is higher than the standard current which set up: 0 - normal, 1 - alarm
    {'id': 'batt_temp_alarm', 'name': 'Temp status', 'long_name': 'Temperature of battery','oid': "41.0",'do_metric': True,'unit': None, 'result': True, 'alarm': BATT_TEMP_ALARM, },		# whether the temperature of the battery is normal or not: 0 - normal, 1 - alarm
    {'id': 'batt_CB_alarm', 'name': 'CB status', 'long_name': 'CB alarm','oid': "42.0",'do_metric': False,'unit': None, 'result': True, 'alarm': BATT_CB_ALARM, },
    {'id': 'batt_blvs_alarm', 'name': 'BLVD', 'long_name': 'BLVD','oid': "45.0",'do_metric': False,'unit': None, 'result': True, 'alarm': BATT_BLVD_ALARM, },				# BLVD --the battery low voltage disconnected: 0 - connected, 1 - disconnected
### Read settings
    {'id': 'batt_charge_overcurrent', 'long_name': 'Battery charge over current point','oid': "56.0",'do_metric': False,'unit': 'a', 'divider':1000},	# 0.001 * batt_charge_overcurrent * batt_capacity --> 0.001*500*100Ah=50A
    {'id': 'batt_llvd_voltage', 'long_name': 'LLVD voltage of battery','oid': "57.0",'do_metric': False,'unit': 'v', 'divider':1000},		# the voltage which to cut off unimportant load
    {'id': 'batt_blvd_voltage', 'long_name': 'BLVDvoltage of battery','oid': "58.0",'do_metric': False,'unit': 'v', 'divider':1000},		# the voltage which to cut off battery to avoid over discharge
    {'id': 'batt_charge_limit', 'long_name': 'Battery charge curent limit', 'oid': '59.0', 'do_metric': False, 'unit': None, },
    {'id': 'batt_charge_cycle', 'long_name': 'The equal charge period','oid': "60.0",'do_metric': False,'unit': '', },
    {'id': 'batt_temp_limit', 'long_name': 'Over Temperature limit','oid': "61.0",'do_metric': False,'unit': 'c', 'divider':1000},
    {'id': 'batt_capacity', 'long_name': 'Battery capacity', 'oid': '62.0', 'do_metric': False, 'unit': 'Ah', },
    {'id': 'batt_charge_protect_time', 'long_name': 'Equal charge keeping time','oid': "63.0",'do_metric': False,'unit': '', },
    {'id': 'batt_eq_charge_time', 'long_name': 'Trickle charge time','oid': "64.0",'do_metric': False,'unit': '', },
    {'id': 'batt_eq_charge_current_limit', 'long_name': 'Current value when battery charge current','oid': "65.0",'do_metric': False,'unit': 'a', 'divider':1000 },
    {'id': 'batt_eq_charge_soc', 'long_name': 'Soc value when battery remain soc level', 'oid': '66.0', 'do_metric': False, 'unit': '%', 'divider': 10 },
    {'id': 'batt_charge_efficient', 'long_name': 'Charge efficient of battery','oid': "67.0",'do_metric': False,'unit': '', },
    {'id': 'batt_eq', 'long_name': 'auto equals enable','oid': "68.0",'do_metric': False,'unit': None, },
]


def parse_jetpower_cas02_batt(string_table):
    parameters = string_table[0]
    for n in range(len(parameters)):
        divider =  BATT_OIDs[n].get('divider') if BATT_OIDs[n].get('divider') else 1
        if _isInt(parameters[n]) and divider == 1:
            value = int(parameters[n])
        elif _isFloat(parameters[n]):
            value = float(int(parameters[n]) / divider)
        else:
            value = str(parameters[n])
            if (value is None) or (value == ''):
                value = chr(216)
        parameters[n] = value
    return parameters


def discover_jetpower_cas02_batt(section):
    yield Service(item="JetPower Batteries")


def check_jetpower_cas02_batt(item, params, section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data")
        return

    state = State.OK
    summary = None
    notice = None
    details = ""

    if item == "JetPower Batteries":

        for n in range(len(section)):
            param = BATT_OIDs[n].get('id')
            value = section[n]

            name = BATT_OIDs[n].get('name') if BATT_OIDs[n].get('name') else None
            long_name = BATT_OIDs[n].get('long_name')
            do_metric = BATT_OIDs[n].get('do_metric') if BATT_OIDs[n].get('do_metric') else False
            unit = BATT_OIDs[n].get('unit') if BATT_OIDs[n].get('unit') else ''
            result = BATT_OIDs[n].get('result') if BATT_OIDs[n].get('result') else False

            if BATT_OIDs[n].get('alarm'):
                value_name = BATT_OIDs[n].get('alarm').get(str(value)).get('name')
                status = BATT_OIDs[n].get('alarm').get(str(value)).get('status')
                details = f"{long_name}: {value_name}{unit}"
                summary = f"{name}: {value_name}{unit}"
            else:
                details = f"{long_name}: {value}{unit}"
                summary = f"{name}: {value}{unit}"

            if do_metric and result and not BATT_OIDs[n].get('alarm'):
                yield from check_levels(
                            value=value,
                            metric_name = param,
                            label = name,
#                            levels_upper = upper_levels,
#                            levels_lower = lower_levels,
                            render_func = lambda parameter_data: _render_func(value, unit),
                        )
            elif do_metric and result:
                yield Metric(param, value)
                yield Result(state=state, details=details, summary=summary)
            elif result:
                yield Result(state=state, details=details, summary=summary)

        return

    yield Result(state=State.UNKNOWN, summary="No item or data")
    return


register.snmp_section(
    name=NAME + "_batt",
    fetch = SNMPTree(
	base = SNMP_BASE,
        oids = [ oid['oid'] for oid in BATT_OIDs],
    ),
    detect = SNMP_DETECT,
    parse_function = parse_jetpower_cas02_batt,
)


register.check_plugin(
    name = NAME + "_batt",
    sections=[NAME+"_batt"],
    service_name = "%s",
    discovery_function = discover_jetpower_cas02_batt,
    check_default_parameters={},
    check_ruleset_name='',
    check_function = check_jetpower_cas02_batt,
)

