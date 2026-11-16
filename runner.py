# -*- coding: utf-8 -*-
"""
Intelligent Traffic Signal Control System (Adaptive Timing & Emergency Vehicle Preemption)

This module controls a single intersection using the SUMO TraCI interface.
It features:
1. Dynamic signal timing based on real-time lane queue lengths.
2. Maximum green light duration limits to prevent lane starvation.
3. Emergency Vehicle Preemption (EVP) based on distance to the traffic light, 
   dynamically extending yellow light buffers for safety.
"""

from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import random

# Locate SUMO tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa


def generate_routefile():
    """
    Generates the route file (cross.rou.xml) for the simulation.
    Creates random traffic flows with a certain percentage of emergency vehicles.
    """
    random.seed(42)  # Fixed seed for reproducibility
    N = 3600         # Total simulation time (seconds)
    
    # Demand generation probabilities per second
    p_we = 1. / 10
    p_ew = 1. / 13
    p_ns = 1. / 50
    p_sn = 1. / 60
    
    # Ratio of emergency vehicles
    special_ratio = 0.2

    with open("data/cross.rou.xml", "w") as routes:
        # Define vehicle types and routes
        print("""<routes>
        <!-- East-West Normal Cars -->
        <vType id="car_we" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" guiShape="passenger"/>
        <!-- North-South Normal Cars -->
        <vType id="car_ns" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" guiShape="passenger"/>
        <!-- East-West Emergency Vehicles (Ambulance) -->
        <vType id="special_we" accel="0.8" decel="4.5" sigma="0.5" length="6" minGap="2.5" maxSpeed="20" vClass="emergency" color="1,0,0"/>
        <!-- North-South Emergency Vehicles (Fire Truck) -->
        <vType id="special_ns" accel="0.8" decel="4.5" sigma="0.5" length="7" minGap="3" maxSpeed="20" vClass="emergency" color="0,0,1"/>

        <!-- Define 4 routes -->
        <route id="route_we" edges="51o 1i 2o 52i" /> <!-- West -> East -->
        <route id="route_ew" edges="52o 2i 1o 51i" /> <!-- East -> West -->
        <route id="route_ns" edges="54o 4i 3o 53i" /> <!-- North -> South -->
        <route id="route_sn" edges="53o 3i 4o 54i" /> <!-- South -> North -->
        """, file=routes)
        
        vehNr = 0
        for i in range(N):
            # West -> East (WE)
            if random.uniform(0, 1) < p_we:
                if random.uniform(0, 1) < special_ratio:
                    print('    <vehicle id="special_we_%i" type="special_we" route="route_we" depart="%i" color="1,0,0"/>' % (vehNr, i), file=routes)
                else:
                    print('    <vehicle id="we_%i" type="car_we" route="route_we" depart="%i"/>' % (vehNr, i), file=routes)
                vehNr += 1
                
            # East -> West (EW)
            if random.uniform(0, 1) < p_ew:
                if random.uniform(0, 1) < special_ratio:
                    print('    <vehicle id="special_ew_%i" type="special_we" route="route_ew" depart="%i" color="1,0,0"/>' % (vehNr, i), file=routes)
                else:
                    print('    <vehicle id="ew_%i" type="car_we" route="route_ew" depart="%i"/>' % (vehNr, i), file=routes)
                vehNr += 1
                
            # North -> South (NS)
            if random.uniform(0, 1) < p_ns:
                if random.uniform(0, 1) < special_ratio:
                    print('    <vehicle id="special_ns_%i" type="special_ns" route="route_ns" depart="%i" color="0,0,1"/>' % (vehNr, i), file=routes)
                else:
                    print('    <vehicle id="ns_%i" type="car_ns" route="route_ns" depart="%i"/>' % (vehNr, i), file=routes)
                vehNr += 1
                
            # South -> North (SN)
            if random.uniform(0, 1) < p_sn:
                if random.uniform(0, 1) < special_ratio:
                    print('    <vehicle id="special_sn_%i" type="special_ns" route="route_sn" depart="%i" color="0,0,1"/>' % (vehNr, i), file=routes)
                else:
                    print('    <vehicle id="sn_%i" type="car_ns" route="route_sn" depart="%i"/>' % (vehNr, i), file=routes)
                vehNr += 1
                
        print("</routes>", file=routes)


def run():
    """
    Main TraCI control loop.
    Implements the state machine for adaptive traffic light control and EV preemption.
    """
    step = 0
    green_duration = 0 
    
    # Initial state: East-West Green (Phase 2)
    current_phase = 2
    traci.trafficlight.setPhase("0", current_phase)
    print("--- Simulation started. Initial state: EW Green (Phase 2) ---")
    
    # Track the last logged emergency vehicle to prevent log spamming
    last_logged_special = None 
    
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        # ---------------------------------------------------------
        # 1. Highest Priority Scan: Detect approaching emergency vehicles
        # ---------------------------------------------------------
        special_vehicle_approaching = None
        special_direction = None
        
        for veh_id in traci.vehicle.getIDList():
            if traci.vehicle.getVehicleClass(veh_id) == "emergency":
                road_id = traci.vehicle.getRoadID(veh_id)
                if road_id in ["51o", "52o", "53o", "54o"]:
                    next_tls = traci.vehicle.getNextTLS(veh_id)
                    if next_tls:
                        dist = next_tls[0][2]  # Distance to the traffic light in meters
                        # Trigger preemption only when EV is within 150 meters
                        if dist <= 150:
                            special_vehicle_approaching = veh_id
                            special_direction = "EW" if road_id in ["51o", "52o"] else "NS"
                            break
        
        # ---------------------------------------------------------
        # 2. Emergency Vehicle Logging
        # ---------------------------------------------------------
        if special_vehicle_approaching:
            if special_vehicle_approaching != last_logged_special:
                if special_direction == "EW":
                    if current_phase == 2:
                        print(f"[{step}s] [INFO] EW Emergency Vehicle {special_vehicle_approaching} detected. Green light already active.")
                    else:
                        print(f"[{step}s] [PREEMPTION] EW Emergency Vehicle {special_vehicle_approaching} detected! Forcing EW Green.")
                elif special_direction == "NS":
                    if current_phase == 0:
                        print(f"[{step}s] [INFO] NS Emergency Vehicle {special_vehicle_approaching} detected. Green light already active.")
                    else:
                        print(f"[{step}s] [PREEMPTION] NS Emergency Vehicle {special_vehicle_approaching} detected! Forcing NS Green.")
                last_logged_special = special_vehicle_approaching
        else:
            last_logged_special = None

        # ---------------------------------------------------------
        # 3. Read queue data for normal vehicles
        # ---------------------------------------------------------
        north_queue = traci.lane.getLastStepHaltingNumber("4i_0")
        south_queue = traci.lane.getLastStepHaltingNumber("3i_0")
        ns_total_queue = north_queue + south_queue
        
        # ---------------------------------------------------------
        # 4. Traffic Light State Machine
        # ---------------------------------------------------------
        # Phase 2: East-West Green
        if current_phase == 2:
            green_duration += 1
            traci.trafficlight.setPhase("0", 2)

            # Switch conditions: Queue threshold met, max timeout reached, or NS EV preemption
            if (green_duration >= 20 and ns_total_queue > 0) or green_duration >= 40 or (special_direction == "NS"):
                current_phase = 3  # Switch to EW Yellow
                traci.trafficlight.setPhase("0", current_phase)
                green_duration = 0
        
        # Phase 3: East-West Yellow
        elif current_phase == 3:
            green_duration += 1
            
            # Dynamic buffer: 5s for EV preemption, 3s for normal transitions
            required_yellow_time = 5 if special_direction == "NS" else 3
            
            if green_duration >= required_yellow_time:
                current_phase = 0  # Switch to NS Green
                traci.trafficlight.setPhase("0", current_phase)
                green_duration = 0
        
        # Phase 0: North-South Green
        elif current_phase == 0:
            green_duration += 1
            traci.trafficlight.setPhase("0", 0)
            
            # Switch conditions: Queue empty and min time reached, max timeout reached, or EW EV preemption
            if (green_duration >= 10 and ns_total_queue == 0) or green_duration >= 30 or (special_direction == "EW"):
                current_phase = 1  # Switch to NS Yellow
                traci.trafficlight.setPhase("0", current_phase)
                green_duration = 0
                
        # Phase 1: North-South Yellow
        elif current_phase == 1:
            green_duration += 1
            
            # Dynamic buffer: 5s for EV preemption, 3s for normal transitions
            required_yellow_time = 5 if special_direction == "EW" else 3
            
            if green_duration >= required_yellow_time:
                current_phase = 2  # Switch to EW Green
                traci.trafficlight.setPhase("0", current_phase)
                green_duration = 0
                
        step += 1
        
    traci.close()
    sys.stdout.flush()


def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="Run the commandline version of sumo (without GUI)")
    options, args = optParser.parse_args()
    return options


if __name__ == "__main__":
    options = get_options()

    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    generate_routefile()

    # Start SUMO simulation and connect via TraCI
    traci.start([sumoBinary, "-c", "data/cross.sumocfg",
                             "--tripinfo-output", "tripinfo.xml"])
    run()