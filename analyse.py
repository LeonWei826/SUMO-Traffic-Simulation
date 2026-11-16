import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt

def analyze_tripinfo(filename="tripinfo.xml"):
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
    except FileNotFoundError:
        print(f"错误：找不到文件 {filename}，请确保仿真已经跑完。")
        return

    # 定义权重（你可以根据需要随时修改这个数值）
    SPECIAL_WEIGHT = 10.0 
    NORMAL_WEIGHT = 1.0

    normal_count = 0
    normal_wait = 0.0
    special_count = 0
    special_wait = 0.0

    # 记录所有车辆的 duration（通过时间）
    all_durations = []
    # 记录特种车辆的 duration（通过时间）
    special_durations = []

    # 遍历所有车辆的行程记录
    for trip in root.findall('tripinfo'):
        veh_id = trip.get('id')
        wait_time = float(trip.get('waitingTime'))
        duration = float(trip.get('duration')) # 通过时间

        all_durations.append(duration)

        # 识别特种车辆
        if "special" in veh_id:
            special_count += 1
            special_wait += wait_time
            special_durations.append(duration)
        else:
            normal_count += 1
            normal_wait += wait_time

    # 1. 分别计算平均等待时间
    avg_normal = normal_wait / normal_count if normal_count > 0 else 0
    avg_special = special_wait / special_count if special_count > 0 else 0

    # 2. 计算总等待时间
    total_raw_wait = normal_wait + special_wait
    
    # 3. 计算加权总等待时间
    weighted_total_wait = (normal_wait * NORMAL_WEIGHT) + (special_wait * SPECIAL_WEIGHT)

    # 计算平均通过时间
    avg_all_duration = sum(all_durations) / len(all_durations) if all_durations else 0
    avg_special_duration = sum(special_durations) / len(special_durations) if special_durations else 0

    # ============= 打印最终成绩单 =============
    print("=========================================")
    print("           🚦 仿真数据深度分析            ")
    print("=========================================")
    print(f"🚗 普通车辆总数: {normal_count} 辆")
    print(f"🚑 特种车辆总数: {special_count} 辆")
    print("-----------------------------------------")
    print(f"⏱️  普通车辆平均等待: {avg_normal:.2f} 秒")
    print(f"⏱️  特种车辆平均等待: {avg_special:.2f} 秒")
    print("-----------------------------------------")
    print(f"📈 传统总等待时间: {total_raw_wait:.2f} 秒")
    print(f"⚖️  加权总等待时间: {weighted_total_wait:.2f} 分")
    print("=========================================")
    
    if avg_special > avg_normal:
        print("⚠️ 警告：特种车辆平均等待时间大于普通车辆，抢占逻辑仍需优化。")
    else:
        print("✅ 表现优异：特种车辆优先通行策略执行得非常完美！")

    # ============= 绘制直方图 =============

    # 设置中文字体，防止乱码
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    # 计算所有车辆的平均等待时间（大盘基线）
    all_avg_wait = (normal_wait + special_wait) / (normal_count + special_count) if (normal_count + special_count) > 0 else 0

    plt.figure(figsize=(10, 6))
    
    # 【核心修改】：只对比“等待时间”这个单一维度！
    labels = ['普通车辆\n平均等待时间', '所有车辆\n平均等待时间', '特种车辆\n平均等待时间']
    values = [avg_normal, all_avg_wait, avg_special]
    colors = ['#4CAF50', '#2196F3', '#FF5722'] # 绿、蓝、红

    bars = plt.bar(labels, values, color=colors, width=0.5)
    
    # 在柱子上标出具体数值
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.2f}s', ha='center', va='bottom', fontsize=14, fontweight='bold')

    plt.title('智能红绿灯控制算法性能指标对比', fontsize=16, fontweight='bold')
    plt.ylabel('平均等待时间 (秒)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # 保存图片
    plt.savefig("benchmark_result.png", dpi=300, bbox_inches='tight')
    print("\n📊 图表已生成并保存为 benchmark_result.png")
    
    plt.show()
if __name__ == "__main__":
    analyze_tripinfo("tripinfo.xml")