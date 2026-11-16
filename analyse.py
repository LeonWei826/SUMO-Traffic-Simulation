# -*- coding: utf-8 -*-
"""
Performance Analysis Script for Intelligent Traffic Signal Control

This script parses the SUMO simulation output (`tripinfo.xml`) to calculate:
1. Average waiting time for normal vehicles vs. emergency vehicles.
2. Weighted total waiting time based on vehicle priority.
3. Visualizes the benchmark results using matplotlib and saves it as a PNG.
"""

import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt

def analyze_tripinfo(filename="tripinfo.xml"):
    """
    Parses tripinfo XML and computes performance metrics.
    """
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found. Please ensure the simulation has completed.")
        return

    # Define weights (can be adjusted based on priority requirements)
    SPECIAL_WEIGHT = 10.0 
    NORMAL_WEIGHT = 1.0

    normal_count = 0
    normal_wait = 0.0
    special_count = 0
    special_wait = 0.0

    # Track durations (total time from depart to arrival)
    all_durations = []
    special_durations = []

    # Iterate through all vehicle trip records
    for trip in root.findall('tripinfo'):
        veh_id = trip.get('id')
        wait_time = float(trip.get('waitingTime'))
        duration = float(trip.get('duration'))

        all_durations.append(duration)

        # Identify emergency vehicles based on ID naming convention
        if "special" in veh_id:
            special_count += 1
            special_wait += wait_time
            special_durations.append(duration)
        else:
            normal_count += 1
            normal_wait += wait_time

    # 1. Calculate average waiting times
    avg_normal = normal_wait / normal_count if normal_count > 0 else 0
    avg_special = special_wait / special_count if special_count > 0 else 0

    # 2. Calculate total raw waiting time
    total_raw_wait = normal_wait + special_wait
    
    # 3. Calculate weighted total waiting time
    weighted_total_wait = (normal_wait * NORMAL_WEIGHT) + (special_wait * SPECIAL_WEIGHT)

    # Calculate average duration
    avg_all_duration = sum(all_durations) / len(all_durations) if all_durations else 0
    avg_special_duration = sum(special_durations) / len(special_durations) if special_durations else 0

    # ============= Print Results =============
    print("=========================================")
    print("       🚦 SIMULATION DATA ANALYSIS       ")
    print("=========================================")
    print(f"🚗 Total Normal Vehicles: {normal_count}")
    print(f"🚑 Total Emergency Vehicles: {special_count}")
    print("-----------------------------------------")
    print(f"⏱️  Avg Normal Vehicle Wait Time: {avg_normal:.2f} s")
    print(f"⏱️  Avg Emergency Vehicle Wait Time: {avg_special:.2f} s")
    print("-----------------------------------------")
    print(f"📈 Raw Total Waiting Time: {total_raw_wait:.2f} s")
    print(f"⚖️  Weighted Total Waiting Time: {weighted_total_wait:.2f} pts")
    print("=========================================")
    
    if avg_special > avg_normal:
        print("⚠️ Warning: Emergency vehicles wait longer than normal vehicles. Preemption logic may need optimization.")
    else:
        print("✅ Success: Emergency vehicle preemption strategy is effective!")

    # ============= Generate Bar Chart =============
    
    # Configure font for cross-platform compatibility (Fallback to default if SimHei is not available)
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

    all_avg_wait = (normal_wait + special_wait) / (normal_count + special_count) if (normal_count + special_count) > 0 else 0

    plt.figure(figsize=(10, 6))
    
    labels = ['Normal Vehicle\nAvg Wait Time', 'All Vehicles\nAvg Wait Time', 'Emergency Vehicle\nAvg Wait Time']
    values = [avg_normal, all_avg_wait, avg_special]
    colors = ['#4CAF50', '#2196F3', '#FF5722'] # Green, Blue, Orange

    bars = plt.bar(labels, values, color=colors, width=0.5)
    
    # Add value labels on top of bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.2f}s', ha='center', va='bottom', fontsize=14, fontweight='bold')

    plt.title('Intelligent Traffic Signal Control - Performance Benchmark', fontsize=16, fontweight='bold')
    plt.ylabel('Average Waiting Time (Seconds)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Save chart
    plt.savefig("benchmark_result.png", dpi=300, bbox_inches='tight')
    print("\n📊 Chart successfully generated and saved as 'benchmark_result.png'")
    
    plt.show()

if __name__ == "__main__":
    analyze_tripinfo("tripinfo.xml")