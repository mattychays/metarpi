from urllib.request import urlopen  
from xml.etree import ElementTree
import csv
import time
import neopixel
import board

airport_list= []
stored_metars = []

color_vfr = (0, 255,0)
color_blink = (255, 255, 255)
color_mvfr = (0,0,255)
color_mvfr_gust = (0,0,200)
color_ifr = (255,0,0)
color_ifr_gust = (200,0,0)
color_lifr = (255,51,153)
color_lifr_gust = (255,51, 100)

#Define Timing Variables
loop_start = time.time()
timer_secs = 0
elapsed_secs = 0
elapsed_mins = 0
flash_wind = False

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

def UpdateMetarData():
    
    getMetarData()

    for airport in airport_list:
        airport.flight_condition = getFlightCondition(airport.icao)
        airport.wind_gusting = getWindConditions(airport.icao, 19)
        print(airport.icao, airport.flight_condition, airport.wind_gusting)

def UpdateAllAirports():
    for airport in airport_list:
        if airport.flight_condition == "VFR":
            pixels[int(airport.led_num)] = color_vfr
        elif airport.flight_condition == "MVFR":
            pixels[int(airport.led_num)] = color_mvfr
        elif airport.flight_condition == "IFR":
            pixels[int(airport.led_num)] = color_ifr
        elif airport.flight_condition == "LIFR":
            pixels[int(airport.led_num)] = color_lifr

def UpdateGustAirports(gust):
    for airport in airport_list:
        if airport.wind_gusting == True:
            if gust == True:
                pixels[int(airport.led_num)] = color_blink
            else:
                if airport.flight_condition == "VFR":
                    pixels[int(airport.led_num)] = color_vfr
                elif airport.flight_condition == "MVFR":
                    pixels[int(airport.led_num)] = color_mvfr
                elif airport.flight_condition == "IFR":
                    pixels[int(airport.led_num)] = color_ifr
                elif airport.flight_condition == "LIFR":
                    pixels[int(airport.led_num)] = color_lifr


#Get Airport ICAOS/Corresponding LED Numbers from Airport.csv
getAirportLedNums()
#Register the LED Strip attached to D18 on the RaspberryPi
pixels = neopixel.NeoPixel(board.D18,50,brightness = .1, pixel_order = neopixel.RGB, auto_write = False)
print("Board Initialized")

#Get Initial Metar Data and Update All Airports
UpdateMetarData()
UpdateAllAirports()

while True:
    timer_secs = time.time() - loop_start
    if timer_secs > 1:
        if flash_wind == True:
            UpdateGustAirports(True)
            flash_wind = False
        else:
            UpdateGustAirports(False)
            flash_wind = True


        if elapsed_secs == 60:
            elapsed_mins = elapsed_mins + 1
            if elapsed_mins == 10:
                UpdateAllAirports()

        #print(pixels)
        pixels.show()
        loop_start = time.time()
        timer_secs = 0
        elapsed_secs = elapsed_secs + 1

