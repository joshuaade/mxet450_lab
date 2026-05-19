#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
import sys
import termios
import tty
import time

class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop_mecanum')

        self.publisher_ = self.create_publisher(
            TwistStamped,
            '/mecanum_drive_controller/cmd_vel',
            10
        )

        self.linear_speed = 0.2
        self.angular_speed = 0.5

        self.settings = termios.tcgetattr(sys.stdin)
        self.get_logger().info("WASD = move, Q/E = rotate, SPACE = stop, CTRL+C to quit")

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        key = sys.stdin.read(1)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def run(self):
        while rclpy.ok():
            key = self.get_key()
            
            msg = TwistStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            if key == 'w':
                msg.twist.linear.x = self.linear_speed
            elif key == 's':
                msg.twist.linear.x = -self.linear_speed
            elif key == 'a':
                msg.twist.linear.y = self.linear_speed
            elif key == 'd':
                msg.twist.linear.y = -self.linear_speed
            elif key == 'q':
                msg.twist.angular.z = self.angular_speed
            elif key == 'e':
                msg.twist.angular.z = -self.angular_speed
            elif key == ' ':
                pass  # zero velocities = stop
            else:
                continue
            self.publisher_.publish(msg)

def main():
    rclpy.init()
    node = KeyboardTeleop()

    try:
        node.run()
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
