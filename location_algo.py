#!/usr/bin/python
import logging
import math
import numpy
import argparse
import csv
import re

logging.basicConfig(filename='/home/akaushik/piri-location-engine/compute_location.log',level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger()

def get_lat_long_for_receiver(receiver):
    return 40.689292,-74.044507

def calculate_distance(rssi, freqInMHz=2412):
    exp = (27.55 - (20 * math.log10(freqInMHz)) + math.fabs(rssi)) / 20.0
    #distance = 10 ^ ((27.55 - (20 * log10(frequency)) + signalLevel) / 20)
    return (math.pow(10.0, exp))/10

def distance_2points(LatA,LonA, LatB, LonB):

    radius = 6371000
    R = radius;
    phy_1 = math.radians(LatA)
    lambda_1 = math.radians(LonA)
    phy_2 = math.radians(LatB)
    lambda_2 = math.radians(LonB)
    delta_phy = phy_2 - phy_1
    delta__lambda = lambda_2 - lambda_1

    a = math.sin(delta_phy / 2) * math.sin(delta_phy / 2) + math.cos(phy_1) * math.cos(phy_2)* math.sin(delta__lambda / 2) * math.sin(delta__lambda / 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c

    return d

def apply_2point_intermediate(uniqueChirpEvents):
    receiver = next(iter(uniqueChirpEvents))
    DistA = float(calculate_distance(uniqueChirpEvents[receiver]))
    LatA, LonA = get_lat_long_for_receiver(receiver)

    receiver = next(iter(uniqueChirpEvents))
    DistB = float(calculate_distance(receiver))
    LatB, LonB = get_lat_long_for_receiver(receiver)
    return apply_2point_intermediate(LatA,LonA, LatB, LonB, DistA, DistB)

def apply_2point_intermediate_points(LatA,LonA, LatB, LonB, DistA, DistB):

    if DistA == 0:
        return LatA, LonA

    if DistB == 0:
        return LatB, LonB

    fraction = DistA/(DistA+DistB)
    _phy_1 = math.radians(LatA)
    _lambda_1 = math.radians(LonA)

    _phy_2 = math.radians(LatB)
    _lambda_2 = math.radians(LonB)

    sin_phy_1 = math.sin(_phy_1)
    cos_phy_1 = math.cos(_phy_1)
    sin_lambda_1 = math.sin(_lambda_1)
    cos_lambda_1 = math.cos(_lambda_1)
    sin_phy_2 = math.sin(_phy_2)
    cos_phy_2 = math.cos(_phy_2)
    sin_lambda_2 = math.sin(_lambda_2)
    cos_lambda_2 = math.cos(_lambda_2)

    # distance between points
    delta__phy_ = _phy_2 - _phy_1
    delta__lambda_ = _lambda_2 - _lambda_1
    a = math.sin(delta__phy_/2) * math.sin(delta__phy_/2) + math.cos(_phy_1) * math.cos(_phy_2) * math.sin(delta__lambda_/2) * math.sin(delta__lambda_/2)

    delta_ = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    A = math.sin((1-fraction)*delta_) / math.sin(delta_)
    B = math.sin(fraction*delta_) / math.sin(delta_)

    x = A * cos_phy_1 * cos_lambda_1 + B * cos_phy_2 * cos_lambda_2
    y = A * cos_phy_1 * sin_lambda_1 + B * cos_phy_2 * sin_lambda_2
    z = A * sin_phy_1 + B * sin_phy_2

    phy_3 = math.atan2(z, math.sqrt(x*x + y*y))
    lambda_3 = math.atan2(y, x)

    return  math.degrees(phy_3), ((math.degrees(lambda_3)+540)%360)-180


def apply_3points(uniqueChirpEvents):
    logger.info("uniqueChirpEvents: %s",uniqueChirpEvents)
    i = 1


    for receiver,rssi in uniqueChirpEvents.items():
        if i == 1:
            DistA = calculate_distance(rssi)
            logger.info("DistA: %s",DistA)
            LatA, LonA = 40.689292, -74.044507
        elif i == 2:
            DistB = calculate_distance(rssi)
            logger.info("DistB: %s", DistB)
            LatB, LonB = 40.701464, -74.01550,
        elif i == 3:
            DistC = calculate_distance(rssi)
            logger.info("DistC: %s", DistC)
            LatC, LonC = 40.674738, -73.9986063
        i = i + 1

    return distance_3points(LatA,LonA, LatB, LonB, LatC, LonC,DistA, DistB, DistC)

def distance_3points(LatA, LonA, LatB, LonB, LatC, LonC, DistA, DistB, DistC):
    # make the points in a 2d tuple if you want to use static points later
    R1 = (LatA, LonA)
    R2 = (LatB, LonB)
    R3 = (LatC, LonC)

    # if d1 ,d2 and d3 in known
    # calculate A ,B and C coifficents

    A = R1[0] ** 2 + R1[1] ** 2 - DistA ** 2
    B = R2[0] ** 2 + R2[1] ** 2 - DistB ** 2
    C = R3[0] ** 2 + R3[1] ** 2 - DistC ** 2

    X32 = R3[0] - R2[0]
    X13 = R1[0] - R3[0]
    X21 = R2[0] - R1[0]

    Y32 = R3[1] - R2[1]
    Y13 = R1[1] - R3[1]
    Y21 = R2[1] - R1[1]

    logger.debug((2.0 * (R1[0] * Y32 + R2[0] * Y13 + R3[0] * Y21)))
    x = (A * Y32 + B * Y13 + C * Y21) / (2.0 * (R1[0] * Y32 + R2[0] * Y13 + R3[0] * Y21))
    y = (A * X32 + B * X13 + C * X21) / (2.0 * (R1[1] * X32 + R2[1] * X13 + R3[1] * X21))
    # prompt the result
    return x, y


def calculate_location(uniqueChirpEvents):
    if len(uniqueChirpEvents) == 2:
        return apply_2point_intermediate()
    elif len(uniqueChirpEvents) == 3:
        return apply_3points(uniqueChirpEvents)

    #pickup top 3 receiver with higher rssi value
    top3UniqueChirpEvents = {}
    top3Counted = 0
    for receiver, rssi in sorted(uniqueChirpEvents.iteritems(), reverse=True):
        if top3Counted == 3:
            break
        top3UniqueChirpEvents[receiver] = uniqueChirpEvents[receiver]
        top3Counted += top3Counted

    return apply_3points(top3UniqueChirpEvents)

if __name__ == '__main__':

    lat, lon =apply_2point_intermediate_points(40.689292, -74.044507,40.701464, -74.015501,1,2)
    print("1:2 Lat: and Lon: ",lat, lon)

    lat, lon = apply_2point_intermediate_points(40.689292, -74.044507, 40.701464, -74.015501, 1, 1)
    print("1:1 Lat: and Lon: ", lat, lon)



    DistA = .312696266935
    DistB = .785457510098
    DistC = .31269626693

    lat, lon = distance_3points(40.689292, -74.044507, 40.701464, -74.015501, 40.782577, -74.1926787,
                                              DistA, DistB, DistC)
    print("Trilateration Lat: and Lon: ", lat, ',', lon)

    d = distance_2points(40.689292, -74.044507, 40.701464, -74.015501)
    print("Distance:%f ",d)

    d = calculate_distance(-80,2412)
    print("-80:  ",d)
    d = calculate_distance(-50, 2412)
    print("-50: ",d)
    d = calculate_distance(-30, 2412)
    print("-30:  ",d)
    d = calculate_distance(-0, 2412)
    print("0:  ",d)
    d = calculate_distance(-100, 2412)
    print("-100: ",d )

