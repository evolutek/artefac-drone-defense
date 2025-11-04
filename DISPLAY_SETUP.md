# Gazebo GUI Display Setup

This guide explains how to configure X11/Display forwarding to see the Gazebo GUI from Docker containers across different operating systems.

---

## Linux (Native X11)

### Prerequisites
- X11 server running (default on most Linux desktop environments)
- `xhost` command available

### Setup Steps

1. **Create Docker X11 authority file:**
```bash
sudo touch /tmp/.docker.xauth
sudo xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | sudo xauth -f /tmp/.docker.xauth nmerge -
sudo chmod 666 /tmp/.docker.xauth
```

2. **Allow Docker to access X11:**
```bash
xhost +local:docker
```

3. **Verify DISPLAY variable in `.env`:**
```bash
DISPLAY=:0
XAUTHORITY=/tmp/.docker.xauth
```

4. **Run containers:**
```bash
docker compose up simulation
```

The Gazebo GUI window should appear automatically.

### Troubleshooting Linux
- If GUI doesn't appear, check: `echo $DISPLAY` (should output `:0` or similar)
- Verify X11 socket: `ls -la /tmp/.X11-unix/`
- Check xauth file: `ls -la /tmp/.docker.xauth`
- Re-run `xhost +local:docker` if you restart your session

---

## macOS

### Prerequisites
- **XQuartz** (X11 server for macOS)

### Setup Steps

1. **Install XQuartz:**
```bash
brew install --cask xquartz
```

2. **Configure XQuartz:**
   - Open XQuartz (Applications → Utilities → XQuartz)
   - Go to XQuartz → Preferences → Security
   - ✅ Enable "Allow connections from network clients"
   - **Restart your Mac** after this change

3. **Start XQuartz and configure access:**
```bash
# Start XQuartz (if not already running)
open -a XQuartz

# Allow connections from localhost
xhost + 127.0.0.1
# Or allow all local connections (less secure)
xhost +local:
```

4. **Update `.env` file:**
```bash
DISPLAY=host.docker.internal:0
XAUTHORITY=/tmp/.docker.xauth
```

5. **Create xauth file:**
```bash
touch /tmp/.docker.xauth
xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f /tmp/.docker.xauth nmerge -
chmod 644 /tmp/.docker.xauth
```

6. **Run containers:**
```bash
docker compose up simulation
```

The Gazebo window should appear in XQuartz.

### Troubleshooting macOS
- Verify XQuartz is running: Check for XQuartz icon in dock/menu bar
- Check DISPLAY: `echo $DISPLAY` (should show `host.docker.internal:0`)
- If GUI doesn't appear, restart XQuartz and re-run `xhost` commands
- Check XQuartz logs: `~/Library/Logs/X11/org.xquartz.log`

---

## Windows (WSL2)

### Prerequisites
- **WSL2** with Ubuntu/Debian
- **VcXsrv** or **X410** (X11 server for Windows)

### Option A: VcXsrv (Free)

1. **Install VcXsrv:**
   - Download from: https://sourceforge.net/projects/vcxsrv/
   - Run installer

2. **Configure VcXsrv:**
   - Launch XLaunch
   - Settings:
     - Display: Multiple windows, Display number: 0
     - ✅ Start no client
     - ✅ Disable access control
     - ✅ Native OpenGL
     - ✅ Disable access control (important!)

3. **In WSL2, update `.env`:**
```bash
# Get Windows host IP
export WINDOWS_HOST=$(ip route show | grep -i default | awk '{ print $3}')
echo "DISPLAY=$WINDOWS_HOST:0" >> .env
```

Or manually set in `.env`:
```bash
DISPLAY=<WINDOWS_HOST_IP>:0
XAUTHORITY=/tmp/.docker.xauth
```

4. **Create xauth file (in WSL2):**
```bash
touch /tmp/.docker.xauth
xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f /tmp/.docker.xauth nmerge - 2>/dev/null || true
chmod 644 /tmp/.docker.xauth
```

5. **Allow firewall access:**
   - Windows Defender Firewall → Allow app
   - Allow VcXsrv on Private networks

6. **Run containers:**
```bash
docker compose up simulation
```

### Option B: X410 (Paid)

1. **Install X410** from Microsoft Store

2. **Launch X410:**
   - Right-click X410 tray icon
   - Select "Windowed Apps" mode

3. **In WSL2, update `.env`:**
```bash
DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
XAUTHORITY=/tmp/.docker.xauth
```

4. **Follow steps 4-6 from Option A**

### Troubleshooting Windows
- Ensure VcXsrv/X410 is running (check system tray)
- Verify firewall allows X server
- Test connection: `xeyes` (install with `sudo apt install x11-apps`)
- Check DISPLAY value: `echo $DISPLAY`
- Try disabling WSL2 firewall: `sudo ufw disable`

---

## Headless Mode (No GUI)

If you don't need the GUI or are running on a server without display:

### Update `.env`:
```bash
HEADLESS=1
```

This will:
- Run Gazebo in server-only mode (`gz sim -s`)
- Skip X11 configuration
- Reduce CPU/GPU usage
- Still allow MAVROS and backend to connect

### Use cases for headless mode:
- CI/CD pipelines
- Remote servers
- Automated testing
- When you only need sensor data, not visualization

---

## Configuration Summary Table

| OS | X11 Server | DISPLAY Value | Special Setup |
|----|-----------|---------------|---------------|
| **Linux** | Native | `:0` | `xhost +local:docker` |
| **macOS** | XQuartz | `host.docker.internal:0` | Enable network clients in XQuartz prefs |
| **Windows (WSL2)** | VcXsrv/X410 | `<HOST_IP>:0` | Disable access control, firewall rules |
| **Headless** | None | N/A | Set `HEADLESS=1` in `.env` |

---

## Testing X11 Connection

Before running Gazebo, test X11 forwarding:

```bash
# Install test tools
sudo apt update && sudo apt install -y x11-apps

# Test with simple GUI
docker run --rm -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /tmp/.docker.xauth:/tmp/.docker.xauth:rw \
  -e XAUTHORITY=/tmp/.docker.xauth \
  ubuntu:22.04 bash -c "apt update && apt install -y x11-apps && xeyes"
```

If `xeyes` appears, X11 forwarding works! ✅

---

## Security Notes

⚠️ **Development vs Production:**

The configurations above use permissive settings (`xhost +`, disable access control) suitable for **local development only**.

For production or shared environments:
- Use proper X11 authentication with xauth cookies
- Don't use `xhost +` (grants access to all)
- Consider VNC or remote desktop instead
- Run in headless mode (`HEADLESS=1`)

---

## Common Issues

### "Cannot open display"
- ✅ Check DISPLAY variable is set
- ✅ Verify X11 server is running
- ✅ Ensure xhost permissions granted
- ✅ Check docker-compose.yml mounts `/tmp/.X11-unix`

### "No protocol specified"
- ✅ Verify `.docker.xauth` file exists and has correct permissions
- ✅ Recreate xauth file with commands above
- ✅ Check XAUTHORITY variable points to correct file

### GUI appears but is blank/frozen
- ✅ Check GPU drivers (especially on Linux)
- ✅ Try software rendering: add `LIBGL_ALWAYS_SOFTWARE=1` to environment
- ✅ Verify Docker has GPU access (if using GPU acceleration)

### WSL2 specific: "Connection refused"
- ✅ Ensure VcXsrv/X410 allows connections from WSL
- ✅ Check Windows firewall
- ✅ Verify DISPLAY IP matches Windows host IP
- ✅ Use `ip route show` to find correct gateway

---

## References

- XQuartz: https://www.xquartz.org/
- VcXsrv: https://sourceforge.net/projects/vcxsrv/
- X410: https://x410.dev/
- Docker X11 Guide: https://wiki.ros.org/docker/Tutorials/GUI
