#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, LaserScan, PointCloud2
from laser_geometry import LaserProjection
import sensor_msgs_py.point_cloud2 as pc2
from cv_bridge import CvBridge
import numpy as np
import cv2

class ScanToCloud(Node):

    
    def __init__(self):
        super().__init__('scan_to_points')
        self.projector = LaserProjection()
        self.bridge = CvBridge()
        self.image = None

        self.subscription_cam = self.create_subscription(
            Image,
            '/cam_1/color/image_raw',
            self.image_callback,
            10)

        self.subscription_lid = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10)
        

    
        self.publisher = self.create_publisher(
            PointCloud2,
            '/cloud',
            10)

    def image_callback(self, msg):
        self.image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def scan_callback(self, scan_msg):
        Transform = np.array([[0.000, -1.000, 0.000, 0.015], [0.479, 0.000, -0.878, -0.079], [0.878, 0.000, 0.479, -0.077], [0.000, 0.000, 0.000, 1.000]])
        K = np.array([[223.4095, 0.000, 212.000], [0.000, 223.4095, 120.000], [0.000, 0.000, 1.000]])
        # Convert LaserScan to PointCloud2
        cloud_msg = self.projector.projectLaser(scan_msg)
        if self.image is None:
            return

        # Publish cloud (optional)
        self.publisher.publish(cloud_msg)

        img = self.image.copy()

        # Extract XYZ points
        cloud_array = np.array((pc2.read_points(
            cloud_msg,
            field_names=("x", "y", "z"),
            skip_nans=True)))
        
        points = np.vstack((cloud_array['x'],
                    cloud_array['y'],
                    cloud_array['z'])).T
        
        R = Transform[:3, :3]
        t = Transform[:3, 3]

        points_cam = (R @ points.T).T + t

        points_cam = points_cam[points_cam[:,2] > 0] # filter out points to only be in front of cam

        uv = (K @ points_cam.T).T

        uv[:,0] /= uv[:,2]
        uv[:,1] /= uv[:,2]
        
        depth = points_cam[:,2]

        colors = np.zeros((len(depth), 3), dtype=np.uint8)

        colors[depth < 1.0] = [0, 0, 255]      # red (near)
        colors[(depth >= 1.0) & (depth < 3.0)] = [0, 255, 255]  # yellow
        colors[depth >= 3.0] = [0, 255, 0] 

        for (u, v), color in zip(uv[:, :2].astype(int), colors):
            if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]:
                img[v, u] = color
            cv2.imshow("Lidar Projection", img)
            cv2.waitKey(1)

        count = 0
        for point in points:
            x, y, z = point
            """pt = np.array([x, y, z])
            lidarpt = np.append(pt,1) # points need to be in 4 x 1 matrix to multiply with transformation matrix
            cam_point = Transform @ lidarpt 
            u = K[0,0] * (cam_point[0] / cam_point[2]) + K[0,2]
            v = K[1,1] * (cam_point[1] / cam_point[2]) + K[1,2]

            if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]:
                depth_color = int(min(255, 255 * cam_point[2] / 10.0))
                cv2.circle(img, (int(u), int(v)), 2, (0, depth_color, 255-depth_color), -1)

            cv2.imshow("Lidar Projection", img)
            cv2.waitKey(1)"""
            count += 1

        self.get_logger().info(f"Converted to {count} points")
        #self.get_logger().info(str(points))



def main(args=None):
    rclpy.init(args=args)
    node = ScanToCloud()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

"""
import rclpy
from rclpy.node import Node
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from sensor_msgs.msg import LaserScan, Image
from cv_bridge import CvBridge
import numpy as np
import os
import cv2


class BagReader(Node):
    def __init__(self):
        super().__init__('bag_reader')

        # Set up bag reader
        #script_dir = os.path.dirname(os.path.realpath(__file__))  # Get the directory of the current script
        #bag_file_path = os.path.join(script_dir, '..', '..', 'bag_files', 'test1')  # Relative path to the bag file
        #bag_file_path = os.path.abspath(bag_file_path)  # Convert to absolute path

        bag_file_path = os.path.expanduser('~/ros2_ws/src/yahboom_rosmaster/yahboom_rosmaster_gazebo/bag_files/test2')

        storage_options = StorageOptions(uri=bag_file_path, storage_id='mcap')
        converter_options = ConverterOptions()
        self.reader = SequentialReader()
        self.reader.open(storage_options, converter_options)

        self.bridge = CvBridge()

        self.lidar_data = []
        self.image_data = []

        self.get_logger().info('Ready to extract data from the bag file...')

    def extract_data(self):
        # Read messages and save Lidar data in binary format
        while self.reader.has_next():
            print("Looped")
            topic, msg, timestamp = self.reader.read_next()
            # Extract LiDAR data
            self.get_logger().info(f"Reading topic: {topic} with message type: {type(msg)}")
            if topic == '/scan' and isinstance(msg, LaserScan):
                print("GAGAGAGA")
                lidar_points = np.array(msg.ranges, dtype=np.float32)
                self.lidar_data.append((timestamp, lidar_points))

            # Extract Camera Image data
            elif topic == '/camera/image_raw' and isinstance(msg, Image):
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
                self.image_data.append((timestamp, cv_image))

    def get_lidar_points(self):

        return self.lidar_data

    def get_image_data(self):

        return self.image_data

def main(args=None):
    rclpy.init(args=args)
    bag_reader = BagReader()
    bag_reader.extract_data()
    lidar_data = bag_reader.get_lidar_points()
    image_data = bag_reader.get_image_data()
    print(lidar_data)
    for timestamp, lidar_points in lidar_data:
        print(f"LiDAR data at timestamp {timestamp}: {lidar_points}")

    for timestamp, image in image_data:
        print(f"Image data at timestamp {timestamp}")
        # Show image (optional)
        cv2.imshow("Camera Image", image)
        cv2.waitKey(1)  # Press any key to close the window
    rclpy.shutdown()

if __name__ == '__main__':
    main()
"""