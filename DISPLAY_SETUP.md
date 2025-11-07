# Gazebo GUI Display Setup

This guide explains how to configure X11/Display forwarding to see the Gazebo GUI from Docker containers across different operating systems.

---

## Quick Start (Recommended)

The project includes an automated setup script that configures X11 for your operating system.

### Setup Steps

1. **Copy `.env.example` to `.env`:**
```bash
cp .env.example .env
```

2. **Set your operating system in `.env`:**
```bash
# Valid values: linux, macos, windows
HOST_OS=linux
```

3. **Start the project:**
```bash
./start.sh up
```

The script will automatically:
- Configure X11/XQuartz based on your `HOST_OS`
- Set up display permissions
- Start Docker Compose services

**That's it!** The Gazebo GUI should appear automatically.

### Available Commands

```bash
./start.sh up          # Start all services
./start.sh up -d       # Start in background (detached)
./start.sh down        # Stop all services
./start.sh restart     # Restart services
```

---

## Manual Setup (Advanced)

If you prefer manual configuration or need to troubleshoot, follow the OS-specific instructions below.

---

## Linux (Native X11)

### Prerequisites
- X11 server running (default on most Linux desktop environments)
- `xhost` command available

### Setup Steps

1. **Set `HOST_OS=linux` in `.env`**

2. **The `./start.sh` script will automatically run:**
```bash
xhost +local:docker
xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f ~/.docker.xauth nmerge -
```

3. **Verify DISPLAY variable in `.env`:**
```bash
DISPLAY=:0
XAUTHORITY=~/.docker.xauth
```

4. **Run with start script:**
```bash
./start.sh up
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

3. **Set `HOST_OS=macos` in `.env`**

4. **The `./start.sh` script will automatically:**
   - Start XQuartz if not running
   - Configure xhost permissions
   - Create the xauth file

5. **Update `.env` file for macOS:**
```bash
HOST_OS=macos
DISPLAY=host.docker.internal:0
XAUTHORITY=~/.docker.xauth
```

6. **Run with start script:**
```bash
./start.sh up
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

3. **Set `HOST_OS=windows` in `.env`**

4. **The `./start.sh` script will automatically:**
   - Detect Windows host IP
   - Configure DISPLAY variable
   - Create xauth file

5. **Update `.env` file for Windows:**
```bash
HOST_OS=windows
# DISPLAY will be auto-configured by the script
# Or manually set:
# DISPLAY=<WINDOWS_HOST_IP>:0
XAUTHORITY=~/.docker.xauth
```

6. **Allow firewall access:**
   - Windows Defender Firewall → Allow app
   - Allow VcXsrv on Private networks

7. **Run with start script:**
```bash
./start.sh up
```

### Option B: X410 (Paid)

1. **Install X410** from Microsoft Store

2. **Launch X410:**
   - Right-click X410 tray icon
   - Select "Windowed Apps" mode

3. **Set `HOST_OS=windows` in `.env` and run:**
```bash
./start.sh up
```

The script will automatically detect and configure the display.

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

| OS | X11 Server | DISPLAY Value | Setup Method |
|----|-----------|---------------|---------------|
| **Linux** | Native | `:0` | Set `HOST_OS=linux` in `.env`, run `./start.sh up` |
| **macOS** | XQuartz | `host.docker.internal:0` | Set `HOST_OS=macos` in `.env`, run `./start.sh up` |
| **Windows (WSL2)** | VcXsrv/X410 | Auto-detected | Set `HOST_OS=windows` in `.env`, run `./start.sh up` |
| **Headless** | None | N/A | Set `HEADLESS=1` in `.env`, use `docker compose up` |

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
