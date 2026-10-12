# topics_quiz

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

一个 ROS1 的激光避障节点：订阅 Kobuki 的激光雷达数据，根据前方 / 左侧 / 右侧的最近障碍距离，
向 `/cmd_vel` 发布速度指令，让机器人在封闭走廊环境中自主前进而不撞墙。

## 功能

节点以 10 Hz 运行，每个周期读取一次激光数据并做四级决策，**优先级从上到下**：

| 条件 | 线速度 `linear.x` | 角速度 `angular.z` | 行为 |
| --- | --- | --- | --- |
| 前方 < 1.0 m | `0.0` | `+0.6` | 原地左转，停止前进避免撞墙 |
| 右侧 < 1.0 m | `0.1` | `+0.5` | 边缓慢前进边左转 |
| 左侧 < 1.0 m | `0.1` | `-0.5` | 边缓慢前进边右转 |
| 以上都不满足 | `0.3` | `0.0` | 直行 |

「前方」优先于两侧，因此当前方和侧面同时有障碍时会选择原地转向，而不是斜着蹭过去。

## 接口

| 方向 | 话题 | 类型 | 说明 |
| --- | --- | --- | --- |
| 订阅 | `/kobuki/laser/scan` | `sensor_msgs/LaserScan` | 激光雷达数据 |
| 发布 | `/cmd_vel` | `geometry_msgs/Twist` | 速度指令 |

## 环境要求

- ROS1（Kinetic / Melodic / Noetic 均可）
- 提供 `/kobuki/laser/scan` 话题的仿真环境或实体 TurtleBot2 / Kobuki

节点为纯 Python 实现，无需编译 C++，`rospy`、`geometry_msgs`、`sensor_msgs` 均为 ROS 自带依赖。

## 使用方法

```bash
# 1. 把本包放进你的 catkin 工作空间的 src 目录
cd ~/catkin_ws/src
# （将 topics_quiz 目录放在这里）

# 2. 编译
cd ~/catkin_ws
catkin_make
source devel/setup.bash

# 3. 运行
roslaunch topics_quiz topics_quiz.launch
```

也可以直接用 `rosrun`：

```bash
rosrun topics_quiz topics_quiz_node.py
```

启动后可以另开终端观察输出话题：

```bash
rostopic echo /cmd_vel
```

## 目录结构

```
topics_quiz/
├── CMakeLists.txt
├── package.xml
├── LICENSE
├── README.md
├── launch/
│   └── topics_quiz.launch      # 启动节点
└── scripts/
    └── topics_quiz_node.py     # 主节点实现
```

## 实现说明

### 激光取值窗口

`scan_callback` 并不使用全部雷达数据，而是只截取三个很小的窗口，目的是避免把两侧的墙
误判成前方障碍：

| 方向 | 取值范围 | 说明 |
| --- | --- | --- |
| 前方 | `ranges[mid-2 : mid+3]` | 取中间 5 个点，`mid = len(ranges) // 2` |
| 右侧 | `ranges[0 : 10]` | 起始 10 个点 |
| 左侧 | `ranges[n-10 : n]` | 末尾 10 个点 |

窗口取得越小，机器人对正前方障碍的反应越干脆，但也越容易漏掉偏斜的障碍物。这个折中
在开阔走廊里表现良好，在狭窄或不规则环境里可能需要调大 `half` 的值。

### 无效值过滤

`LaserScan` 中常出现 `inf`（超出量程或无回波）、`nan`（无效读数）以及小于等于 0 的值
（部分驱动用来表示异常）。`min_valid()` 会把这些值全部剔除后再取最小值；如果整个窗口
没有有效值，则返回 `inf`，视为该方向安全。

### 可调参数

目前以下参数**硬编码**在 `topics_quiz_node.py` 中，尚未暴露为 ROS 参数：

| 参数 | 位置 | 当前值 |
| --- | --- | --- |
| 障碍阈值 | `TopicsQuiz.__init__` 的 `self.threshold` | `1.0` m |
| 控制频率 | `TopicsQuiz.__init__` 的 `self.rate` | `10` Hz |
| 前方窗口半宽 | `scan_callback` 的 `half` | `2` |

如需调整，直接修改源码后重新运行即可。若要通过 launch 文件传参，需要先把它们改成
`rospy.get_param()` 读取。

## 已知限制

- 话题名 `/cmd_vel` 和 `/kobuki/laser/scan` 均**硬编码**，其他机器人平台需要改源码。
- 取值窗口假设激光的索引 0 对应右侧、`n-1` 对应左侧（Kobuki 的排布）。换用其他雷达
  （尤其是索引方向相反的）会得到左右颠倒的转向。
- 决策是纯反应式的有限状态机，没有建图、定位或路径规划，也不保证能走出迷宫，
  只保证不会正面撞墙。
- 没有回退机制：若激光话题停止发布，节点会一直沿用上一次的距离读数继续运动。

## 许可证

本项目采用 [MIT License](./LICENSE) 授权。
