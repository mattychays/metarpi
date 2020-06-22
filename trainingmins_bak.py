from urllib.request import urlopen  
from xml.etree import ElementTree
import csv

airport_list= []
stored_metars = []

class Airport:
    icao = ""
    led_num = 0
    led_color = (0,0, 0)
    flight_condition = "VFR"
    wind_gusting = False

def getMetarData():
    
    icao_list = []

    for airport in airport_list:
        icao_list.append(airport.icao)
    arpt_list = ",".join(icao_list)

    addsUrl = f"https://www.aviationweather.gov/adds/dataserver_current/httpparam?datasource=metars&requestType=retrieve&format=xml&mostRecentForEachStation=constraint&hoursBeforeNow=1.25&stationString={arpt_list}"
    with urlopen(addsUrl) as data:
        xmldata = ElementTree.parse(data)
        
        root = xmldata.getroot()
        
        data_elem = root.find("data")
        metar_list = data_elem.findall("METAR")

        for metar in metar_list:
            metar_params = dict({})
            sky_condition = dict({})
            sky_conditions = []

            for elem in metar:
                metar_params[elem.tag] = elem.text
                if elem.tag == "sky_condition":
                    if elem.attrib["sky_cover"] == "CLR":
                        sky_condition = {"cloud_cover": elem.attrib["sky_cover"], "agl" :-1}
                    else:
                        sky_condition = {"cloud_cover": elem.attrib["sky_cover"], "agl" : elem.attrib["cloud_base_ft_agl"]}
                    sky_conditions.append(sky_condition)

            metar_params["sky_condition"] = sky_conditions
            stored_metars.append(metar_params)

def getTrainingMins(airframe):
    vis_param = 2
    ceiling_param = 500

    if airframe == 2:
        vis_param = 3
        ceiling_param = 700

    vis_good = False
    ceilings_good = True
    trainingmins_good = True

    metar = {}
    for airport_metar in stored_metars:
        if airport_metar["station_id"] == "PADQ":
            metar = airport_metar

    if float(metar["visibility_statute_mi"]) < vis_param:
        vis_good = False

    for sky_condition in metar["sky_condition"]:
        if sky_condition["cloud_cover"] == "OVC" or sky_condition["cloud_cover"] == "BKN":
            if float(sky_condition["agl"]) < ceiling_param:
                ceilings_good = False

    if int(vis_good) + int(ceilings_good) < 2:
        trainingmins_good = False

    print(vis_good,ceilings_good, trainingmins_good) 

def getFlightCondition(icao):
    flight_condition = "VFR"
    for metar in stored_metars:
        if metar["station_id"] == icao:
            return metar["flight_category"]
        
def getWindConditions(icao, gustThreshold):
    for metar in stored_metars:
        if metar["station_id"] == icao:
            if "wind_gust_kt" in metar:
                if float(metar["wind_gust_kt"]) > gustThreshold:
                    return True
            else:
                return False

def getAirportLedNums():
    with open("airports.csv") as csvfile:
        airport_reader = csv.reader(csvfile, delimiter = ",")
        for row in airport_reader:
            airport = Airport()
            airport.icao = row[0]
            airport.led_num = row[1]
            airport_list.append(airport)


def Update():
    getAirportLedNums()
    getMetarData()

    for airport in airport_list:
        airport.flight_condition = getFlightCondition(airport.icao)
        airport.wind_gusting = getWindConditions(airport.icao, 20)

Update()

for airport in airport_list:
    print(airport.icao, airport.flight_condition, airport.wind_gusting)

for metar in stored_metars:
    if "wx_string" in metar:
        if metar["wx_string"].find("RN"):
            print("It's raining @", metar["station_id"])