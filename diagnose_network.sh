#!/bin/bash
# Network and CPU diagnostic script for multi-drone simulation

echo "=== CPU Usage ==="
top -bn1 | grep "Cpu(s)" | awk '{print "CPU Usage: " $2 + $4 "%"}'

echo ""
echo "=== Docker Container CPU/Memory ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo ""
echo "=== Network Interface Traffic ==="
# Get main interface name
INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
echo "Main interface: $INTERFACE"
ip -s link show $INTERFACE | grep -A 1 "RX:\|TX:"

echo ""
echo "=== Active Network Connections (UDP multicast on ports 7400-7420) ==="
# Check for DDS discovery traffic
ss -u -a | grep -E "7400|7410|7420" || echo "No active DDS discovery ports found"

echo ""
echo "=== Multicast Group Membership ==="
# Check multicast group membership (modern method)
ip maddress show dev $INTERFACE 2>/dev/null | head -20 || echo "Could not read multicast groups"

echo ""
echo "=== ROS2 Topic Bandwidth (top 5) ==="
docker exec -it artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && timeout 5 ros2 topic bw --window 10 2>/dev/null | head -20" || echo "Could not measure (container not running)"

echo ""
echo "=== FastDDS Multicast Configuration ==="
if [ -f simulation/config/fastdds.xml ]; then
    grep -A 5 "multicast\|whitelist" simulation/config/fastdds.xml || echo "No multicast config found"
else
    echo "fastdds.xml not found"
fi
