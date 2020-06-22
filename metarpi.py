from urllib.request import urlopen  
from xml.etree import ElementTree
import csv
import datetime
import time
import neopixel
import board

addsURL = ""
#Create Lists to Store Airport/Metar Data
airport_list= []
stored_metars = []

#define LED Color Values
color_vfr = (0, 255,0)
color_mvfr = (0,0,255)
color_ifr = (255,0,0)
color_lifr = (255,51,153)
color_blink = (255,255,255)

#Define Timing Variables
loop_start = time.time()
timer_secs = 0
elapsed_secs = 0
elapsed_mins = 0
flash_wind = False

#Define Airport Class
class Airport:
    icao = ""
    led_num = 0
    led_color = (0,0, 0)
    flight_condition = "VFR"
    wind_gusting = False
    rawMETAR = ""

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

    return addsUrl

def getTrainingMins(airframe):
    vis_param = 2.0
    ceiling_param = 500

    if airframe == 2:
        vis_param = 3.0
        ceiling_param = 700

    vis_good = True
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
        #print( int(vis_good))
        trainingmins_good = False

    return trainingmins_good


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
    addsURL = getMetarData()
    print("Requesting METAR Data from: \n")
    print(addsURL, "\n")
    print("METAR Data Updated at:", datetime.datetime.now())
    print("----------------------------------")
    for airport in airport_list:
        airport.flight_condition = getFlightCondition(airport.icao)
        airport.wind_gusting = getWindConditions(airport.icao, 15)
        print(f"ICAO: {airport.icao} | Flight Condition: {airport.flight_condition} | Gusting: {airport.wind_gusting}")
    print("----------------------------------")

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

def UpdateTrainingMins(ledNum, trainingmins):
    if trainingmins:
        pixels[ledNum] = color_vfr
    else:
        pixels[ledNum] = color_ifr

#Get Airport ICAOS/Corresponding LED Numbers from Airport.csv
getAirportLedNums()
#Register the LED Strip attached to D18 on the RaspberryPi
pixels = neopixel.NeoPixel(board.D18,50,brightness = .1, pixel_order = neopixel.RGB, auto_write = False)
print("Welcome to MetarPi\n")
print("Log: Board Initialized\n")

#Get Initial Metar Data and Update All Airports
UpdateMetarData()
UpdateAllAirports()

RW_training_mins = getTrainingMins(1)
FW_training_mins = getTrainingMins(2)

UpdateTrainingMins(0, getTrainingMins(2))
UpdateTrainingMins(1, getTrainingMins(1))

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

            if elapsed_mins == 2:
                UpdateMetarData()
                UpdateAllAirports()
                UpdateTrainingMins(0, getTrainingMins(2))
                UpdateTrainingMins(1, getTrainingMins(1))
                elapsed_mins = 0
            elapsed_secs = 0

        pixels.show()
        loop_start = time.time()
        timer_secs = 0 
        elapsed_secs = elapsed_secs + 1

