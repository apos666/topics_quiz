#!/usr/bin/env python3

import math
import rospy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan


class TopicsQuiz:
    def __init__(self):
        rospy.init_node('topics_quiz_node', anonymous=False)

        self.cmd_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.scan_sub = rospy.Subscriber(
            '/kobuki/laser/scan',
            LaserScan,
            self.scan_callback
        )

        self.rate = rospy.Rate(10)
        self.threshold = 1.0

        self.front = float('inf')
        self.left = float('inf')
        self.right = float('inf')

    @staticmethod
    def min_valid(values):
        """返回一组激光值中最近的有效障碍距离，忽略 inf / nan / 0"""
        valid = []
        for r in values:
            if math.isnan(r) or math.isinf(r):
                continue
            if r <= 0.0:
                continue
            valid.append(r)
        return min(valid) if valid else float('inf')

    def scan_callback(self, msg):
        ranges = msg.ranges
        n = len(ranges)
        if n == 0:
            return

        # 只取很小的窗口，避免把侧面的墙误判成前方
        mid = n // 2
        half = 2  # 正前方取中间 5 个点

        front_slice = ranges[max(0, mid - half): min(n, mid + half + 1)]
        # 右侧取开头一小段
        right_slice = ranges[0: min(n, 10)]
        # 左侧取结尾一小段
        left_slice = ranges[max(0, n - 10): n]

        self.front = self.min_valid(front_slice)
        self.right = self.min_valid(right_slice)
        self.left = self.min_valid(left_slice)

    def run(self):
        while not rospy.is_shutdown():
            twist = Twist()

            if self.front < self.threshold:
                # 前方有障碍：原地左转，线速度为 0，避免继续前进撞墙
                twist.linear.x = 0.0
                twist.angular.z = 0.6

            elif self.right < self.threshold:
                # 右侧有障碍：左转，稍微前进
                twist.linear.x = 0.1
                twist.angular.z = 0.5

            elif self.left < self.threshold:
                # 左侧有障碍：右转，稍微前进
                twist.linear.x = 0.1
                twist.angular.z = -0.5

            else:
                # 前方、左侧、右侧都安全：直行
                twist.linear.x = 0.3
                twist.angular.z = 0.0

            self.cmd_pub.publish(twist)
            self.rate.sleep()


if __name__ == '__main__':
    try:
        node = TopicsQuiz()
        node.run()
    except rospy.ROSInterruptException:
        pass