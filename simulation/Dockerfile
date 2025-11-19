# Arguments de build (doivent être avant FROM)
ARG ROS_DISTRO=humble
ARG UBUNTU_VERSION=jammy

FROM osrf/ros:${ROS_DISTRO}-desktop-full-${UBUNTU_VERSION}

# Métadonnées
LABEL maintainer="Evolutek Team"
LABEL description="ROS2 Humble workspace with MAVROS and Gazebo Harmonic integration for drone swarm simulation"
LABEL ros.distro="${ROS_DISTRO}"
LABEL gazebo.version="Harmonic"

# Arguments de build
ARG DEBIAN_FRONTEND=noninteractive

# Install basic tools first
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Add Gazebo Harmonic repository
RUN wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
    | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null

# Installation dépendances système
RUN apt-get update && apt-get install -y \
    # Build tools
    build-essential \
    cmake \
    git \
    # Python
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    python3-paho-mqtt \
    # ROS2 packages
    ros-${ROS_DISTRO}-ros-gz \
    ros-${ROS_DISTRO}-mavros \
    ros-${ROS_DISTRO}-mavros-extras \
    ros-${ROS_DISTRO}-geographic-info \
    ros-${ROS_DISTRO}-tf-transformations \
    ros-${ROS_DISTRO}-robot-localization \
    # SLAM/Navigation (à activer selon besoins)
    # ros-${ROS_DISTRO}-rtabmap-ros \
    # ros-${ROS_DISTRO}-navigation2 \
    # Outils debug
    ros-${ROS_DISTRO}-rqt \
    ros-${ROS_DISTRO}-rqt-common-plugins \
    # Gazebo Harmonic
    gz-harmonic \
    # Gazebo Transport for Python bindings (vision bridge)
    libgz-transport13-dev \
    python3-gz-transport13 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Installation GeographicLib datasets (pour MAVROS)
# Use the script provided by the MAVROS package instead of downloading from GitHub
RUN . /opt/ros/${ROS_DISTRO}/setup.sh \
    && ros2 run mavros install_geographiclib_datasets.sh

# Install Flask for simulation control server
RUN pip3 install --no-cache-dir flask flask-cors

# Setup workspace
WORKDIR /root/ros2_ws

# Create src directory and copy sources
RUN mkdir -p src
COPY src/ src/

# Configuration FastDDS (optimisé pour multi-drones)
COPY config/fastdds.xml /root/fastdds.xml

# Copy simulation control scripts and server
COPY spawn_drone.sh /root/spawn_drone.sh
COPY despawn_drone.sh /root/despawn_drone.sh
COPY spawn_zone.sh /root/spawn_zone.sh
COPY despawn_zone.sh /root/despawn_zone.sh
COPY simulation_control_server.py /root/simulation_control_server.py
RUN chmod +x /root/*.sh /root/simulation_control_server.py

# Copy exclusion zone SDF model
COPY models/exclusion_zone /root/models/exclusion_zone

# Initialisation rosdep
RUN rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y || true

# Build workspace (only if src/ has packages)
RUN . /opt/ros/${ROS_DISTRO}/setup.sh && \
    if [ "$(ls -A src)" ]; then \
        colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release; \
    else \
        echo "No packages to build in src/"; \
    fi

# Configuration shell
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc && \
    echo "if [ -f /root/ros2_ws/install/setup.bash ]; then source /root/ros2_ws/install/setup.bash; fi" >> ~/.bashrc && \
    echo "export ROS_DOMAIN_ID=\${ROS_DOMAIN_ID:-42}" >> ~/.bashrc && \
    echo "export RCUTILS_COLORIZED_OUTPUT=1" >> ~/.bashrc && \
    echo "export FASTRTPS_DEFAULT_PROFILES_FILE=/root/fastdds.xml" >> ~/.bashrc

# Aliases utiles
RUN echo "alias cb='colcon build --symlink-install'" >> ~/.bashrc && \
    echo "alias cbs='colcon build --symlink-install --packages-select'" >> ~/.bashrc && \
    echo "alias rt='ros2 topic'" >> ~/.bashrc && \
    echo "alias rn='ros2 node'" >> ~/.bashrc

# Create entrypoint
RUN echo '#!/bin/bash\n\
set -e\n\
source /opt/ros/'${ROS_DISTRO}'/setup.bash\n\
if [ -f /root/ros2_ws/install/setup.bash ]; then\n\
    source /root/ros2_ws/install/setup.bash\n\
fi\n\
exec "$@"\n\
' > /root/entrypoint.sh && chmod +x /root/entrypoint.sh

WORKDIR /root/ros2_ws
ENTRYPOINT ["/root/entrypoint.sh"]

CMD ["/bin/bash"]
