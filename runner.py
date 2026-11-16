# 更加真实的模拟十字路口（含特殊车辆最高优先级抢占）
from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import random

# 加载 SUMO tools 目录
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa


def generate_routefile():
    random.seed(42)  # 固定随机种子，保证实验可复现
    N = 3600  # 仿真总时长 3600 秒
    
    # 各方向车辆生成概率
    p_we = 1. / 10
    p_ew = 1. / 13
    p_ns = 1. / 50
    p_sn = 1. / 60
    
    # 特殊车辆占比
    special_ratio = 0.2

    with open("data/cross.rou.xml", "w") as routes:
        # 定义车辆类型与路线
        print("""<routes>
        <!-- 东西向普通小汽车 -->
        <vType id="car_we" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" guiShape="passenger"/>
        <!-- 南北向普通小汽车 -->
        <vType id="car_ns" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" guiShape="passenger"/>
        <!-- 东西向特殊车辆（救护车） -->
        <vType id="special_we" accel="0.8" decel="4.5" sigma="0.5" length="6" minGap="2.5" maxSpeed="20" vClass="emergency" color="1,0,0"/>
        <!-- 南北向特殊车辆（消防车） -->
        <vType id="special_ns" accel="0.8" decel="4.5" sigma="0.5" length="7" minGap="3" maxSpeed="20" vClass="emergency" color="0,0,1"/>

        <!-- 定义 4 条路线 -->
        <route id="route_we" edges="51o 1i 2o 52i" /> <!-- 西 -> 东 -->
        <route id="route_ew" edges="52o 2i 1o 51i" /> <!-- 东 -> 西 -->
        <route id="route_ns" edges="54o 4i 3o 53i" /> <!-- 北 -> 南 -->
        <route id="route_sn" edges="53o 3i 4o 54i" /> <!-- 南 -> 北 -->
        """, file=routes)
        
        vehNr = 0
        for i in range(N):
            # 西向东 (WE)
            if random.uniform(0, 1) < p_we:
                if random.uniform(0, 1) < special_ratio:
                    vtype = "special_we"
                    color_str = ' color="1,0,0"'
                    # 【关键修改】给特种车改个含有 special 的名字
                    print('    <vehicle id="special_we_%i" type="%s" route="route_we" depart="%i"%s/>' % (vehNr, vtype, i, color_str), file=routes)
                else:
                    print('    <vehicle id="we_%i" type="car_we" route="route_we" depart="%i"/>' % (vehNr, i), file=routes)
                vehNr += 1
                
            # 东向西 (EW)
            if random.uniform(0, 1) < p_ew:
                if random.uniform(0, 1) < special_ratio:
                    vtype = "special_we"
                    color_str = ' color="1,0,0"'
                    print('    <vehicle id="special_ew_%i" type="%s" route="route_ew" depart="%i"%s/>' % (vehNr, vtype, i, color_str), file=routes)
                else:
                    print('    <vehicle id="ew_%i" type="car_we" route="route_ew" depart="%i"/>' % (vehNr, i), file=routes)
                vehNr += 1
                
            # 北向南 (NS)
            if random.uniform(0, 1) < p_ns:
                if random.uniform(0, 1) < special_ratio:
                    vtype = "special_ns"
                    color_str = ' color="0,0,1"'
                    print('    <vehicle id="special_ns_%i" type="%s" route="route_ns" depart="%i"%s/>' % (vehNr, vtype, i, color_str), file=routes)
                else:
                    print('    <vehicle id="ns_%i" type="car_ns" route="route_ns" depart="%i"/>' % (vehNr, i), file=routes)
                vehNr += 1
                
            # 南向北 (SN)
            if random.uniform(0, 1) < p_sn:
                if random.uniform(0, 1) < special_ratio:
                    vtype = "special_ns"
                    color_str = ' color="0,0,1"'
                    print('    <vehicle id="special_sn_%i" type="%s" route="route_sn" depart="%i"%s/>' % (vehNr, vtype, i, color_str), file=routes)
                else:
                    print('    <vehicle id="sn_%i" type="car_ns" route="route_sn" depart="%i"/>' % (vehNr, i), file=routes)
                vehNr += 1
                
        print("</routes>", file=routes)


def run():
    """智能红绿灯控制循环"""
    step = 0
    green_duration = 0 
    
    # 初始状态：东西绿灯（相位 2）
    current_phase = 2
    traci.trafficlight.setPhase("0", current_phase)
    print("--- 仿真开始，初始状态：东西绿灯 (Phase 2) ---")
    
    # 记录上一秒是否有特种车，防止日志刷屏
    last_printed_special = None 
    
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        # 1. 最高优先级扫描：检测特种车辆
        special_vehicle_approaching = None
        special_direction = None
        
        for veh_id in traci.vehicle.getIDList():
            if traci.vehicle.getVehicleClass(veh_id) == "emergency":
                road_id = traci.vehicle.getRoadID(veh_id)
                if road_id in ["51o", "52o", "53o", "54o"]:
                    next_tls = traci.vehicle.getNextTLS(veh_id)
                    if next_tls:
                        dist = next_tls[0][2]  # next_tls[0][2] 就是距离信号灯的米数
                        # 仅当距离 <= 150 米时，才触发抢占
                        if dist <= 150:
                            special_vehicle_approaching = veh_id
                            special_direction = "EW" if road_id in ["51o", "52o"] else "NS"
                            break
        
        # 2. 特种车辆日志与控制逻辑
        if special_vehicle_approaching:
            if special_vehicle_approaching != last_printed_special:
                if special_direction == "EW":
                    if current_phase == 2:
                        print(f"[{step}s] ✅ 检测到东西向特种车 {special_vehicle_approaching}，前方已是绿灯，顺畅通过。")
                    else:
                        print(f"[{step}s] 🚨 紧急抢占！检测到东西向特种车 {special_vehicle_approaching}，即将强制切东西绿灯！")
                elif special_direction == "NS":
                    if current_phase == 0:
                        print(f"[{step}s] ✅ 检测到南北向特种车 {special_vehicle_approaching}，前方已是绿灯，顺畅通过。")
                    else:
                        print(f"[{step}s] 🚨 紧急抢占！检测到南北向特种车 {special_vehicle_approaching}，即将强制切南北绿灯！")
                last_printed_special = special_vehicle_approaching
        else:
            last_printed_special = None

        # 3. 普通车辆排队数据
        north_queue = traci.lane.getLastStepHaltingNumber("4i_0")
        south_queue = traci.lane.getLastStepHaltingNumber("3i_0")
        ns_total_queue = north_queue + south_queue
        
        # 4. 红绿灯状态机
        # --- 东西绿灯（相位 2） ---
        if current_phase == 2:
            green_duration += 1
            traci.trafficlight.setPhase("0", 2)

            # 切换条件：普通感应、强制超时、或者南北有特种车
            if (green_duration >= 20 and ns_total_queue > 0) or green_duration >= 40 or (special_direction == "NS"):
                current_phase = 3  # 切到东西黄灯
                traci.trafficlight.setPhase("0", current_phase)
                green_duration = 0
        
        # --- 东西黄灯（相位 3） ---
        elif current_phase == 3:
            green_duration += 1
            
            # 【黄灯时长判断】：如果是为南北特种车让路，等 5 秒；普通情况等 3 秒
            required_yellow_time = 5 if special_direction == "NS" else 3
            
            if green_duration >= required_yellow_time:
                current_phase = 0
                traci.trafficlight.setPhase("0", current_phase)
                green_duration = 0
        
        # --- 南北绿灯（相位 0） ---
        elif current_phase == 0:
            green_duration += 1
            traci.trafficlight.setPhase("0", 0)
            
            # 切换条件：普通感应、强制超时、或者东西有特种车
            if (green_duration >= 10 and ns_total_queue == 0) or green_duration >= 30 or (special_direction == "EW"):
                current_phase = 1  # 切到南北黄灯
                traci.trafficlight.setPhase("0", current_phase)
                green_duration = 0
                
        # --- 南北黄灯（相位 1） ---
        elif current_phase == 1:
            green_duration += 1
            
            # 【黄灯时长判断】：如果是为东西特种车让路，等 5 秒；普通情况等 3 秒
            required_yellow_time = 5 if special_direction == "EW" else 3
            
            if green_duration >= required_yellow_time:
                current_phase = 2
                traci.trafficlight.setPhase("0", current_phase)
                green_duration = 0
                
        step += 1
        
    traci.close()
    sys.stdout.flush()


def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options


if __name__ == "__main__":
    options = get_options()

    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    generate_routefile()

    traci.start([sumoBinary, "-c", "data/cross.sumocfg",
                             "--tripinfo-output", "tripinfo.xml"])
    run()