from setuptools import setup
import os
from glob import glob

package_name = 'mqtt_bridge'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Evolutek',
    maintainer_email='dev@evolutek.org',
    description='MQTT bridge for drone telemetry and command relay',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'bridge_node = mqtt_bridge.bridge_node:main',
            'vision_pose_bridge = mqtt_bridge.vision_pose_bridge:main',
        ],
    },
)
