# Simulation Control Mobile App

**Expo React Native application** for controlling the Artefac Drone Defense Gazebo simulation from a tablet or mobile device.

## Features

- ✅ **Spawn drones dynamically** with custom position or auto-grid
- ✅ **Remove drones** with confirmation dialog
- ✅ **Create exclusion zones** (jamming, no-fly, restricted)
- ✅ **Delete zones** from simulation
- ✅ **Real-time dashboard** with active drones and zones lists
- ✅ **Multi-platform**: iOS, Android, and Web (PWA)

---

## Prerequisites

- **Node.js** 18+ and npm
- **Expo CLI**: `npm install -g expo-cli` (optional, can use `npx expo` instead)
- **Backend server** running (simulation control Flask server on port 8080)

For mobile development:
- **iOS**: Expo Go app or Xcode (macOS only)
- **Android**: Expo Go app or Android Studio
- **Web**: Any modern browser

---

## Installation

```bash
cd mobile
npm install
```

---

## Configuration

### API URL Setup

The app needs to know where the Flask simulation control server is running (port 8080).

**Default behavior:**
- **Web**: `http://localhost:8080` (assumes Docker running on same machine)
- **Android emulator**: `http://10.0.2.2:8080`
- **iOS simulator**: `http://localhost:8080`
- **Real device**: You need to configure the server IP

**To override the default**, set the environment variable:

```bash
# .env file (create in mobile/ directory)
EXPO_PUBLIC_API_URL=http://192.168.1.100:8080
```

Replace `192.168.1.100` with your Docker host IP address.

---

## Running the App

### Development Mode

#### Web (Easiest for testing)
```bash
npm run web
```

Opens in browser at `http://localhost:8081` (or next available port).

#### iOS Simulator (macOS only)
```bash
npm run ios
```

#### Android Emulator
```bash
npm run android
```

#### On Physical Device (via Expo Go app)
```bash
npx expo start
```

Then scan the QR code with:
- **iOS**: Camera app
- **Android**: Expo Go app

---

### Production Builds

#### Web (PWA - Progressive Web App)
```bash
npx expo export:web
```

Output in `web-build/` directory. Serve with any static file server (Nginx, Apache, etc.).

**Deploy example with Nginx:**
```bash
# Copy build to Nginx web root
cp -r web-build/* /var/www/html/simulation-control/

# Or serve locally for testing
npx serve web-build
```

#### Android APK
```bash
# Using EAS Build (recommended)
npm install -g eas-cli
eas build --platform android

# Or local build (requires Android Studio)
npx expo run:android --variant release
```

#### iOS IPA
```bash
# Using EAS Build (requires Apple Developer account)
eas build --platform ios
```

---

## Usage

### 1. Launch Backend Server

Ensure the Docker containers are running:

```bash
# From project root
docker compose up
```

The simulation control server should be accessible at `http://localhost:8080/health`.

**Verify server is running:**
```bash
curl http://localhost:8080/health
# Should return: {"status":"healthy","service":"simulation-control",...}
```

### 2. Launch Mobile App

```bash
cd mobile
npm run web  # or npm run android / npm run ios
```

### 3. Control Simulation

**Spawn a drone:**
1. Go to "Drones" tab
2. Toggle "Custom Position" ON to specify coordinates, or leave OFF for auto-grid
3. Tap "Spawn Drone"
4. Wait ~15 seconds for drone to be ready
5. Drone appears in "Active Drones" list below

**Remove a drone:**
1. Find drone in "Active Drones" list
2. Tap "Remove" button
3. Confirm deletion
4. Drone disappears from Gazebo simulation

**Create exclusion zone:**
1. Go to "Exclusion Zones" tab
2. Enter zone name (e.g., "Jamming Alpha")
3. Select zone type (Jamming / No-Fly / Restricted)
4. Enter center coordinates (X, Y, Z)
5. Enter radius in meters
6. Tap "Create Zone"
7. Red/orange/yellow cylinder appears in Gazebo

**Delete a zone:**
1. Find zone in "Active Zones" list
2. Tap "Delete" button
3. Confirm deletion
4. Visual marker disappears from Gazebo

---

## Troubleshooting

### "Network Error" when spawning drone

**Problem**: App can't connect to simulation control server.

**Solutions:**
1. **Web**: Check Flask server is running: `curl http://localhost:8080/health`
2. **Mobile device**: Ensure device is on same WiFi network as Docker host
3. **Android emulator**: Use `http://10.0.2.2:8080` (not `localhost`)
4. **iOS simulator**: Use `http://localhost:8080`
5. **Real device**: Set correct server IP in `.env` file

**Check server IP:**
```bash
# Linux/macOS
ipconfig getifaddr en0  # macOS WiFi
ip addr show  # Linux

# Windows (WSL)
ipconfig  # In Windows CMD
```

### SafeAreaView deprecation warnings

**Expected behavior**: These are warnings, not errors. The app works correctly.

**To fix** (optional): Install `react-native-safe-area-context` and replace imports.

### Spawn takes a long time (>30s)

**Expected**: Spawning a drone takes ~10-15 seconds (PX4 startup + MAVROS connection).

**If timeout occurs**: Check Docker container logs:
```bash
docker logs artefac_ros2_integration
```

---

## Project Structure

```
mobile/
├── App.tsx                 # Main app with tabs navigation
├── components/
│   ├── DroneSpawnForm.tsx      # Form to spawn drones
│   ├── ActiveDronesList.tsx    # List of active drones
│   ├── ZoneCreateForm.tsx      # Form to create zones
│   └── ActiveZonesList.tsx     # List of active zones
├── services/
│   └── api.ts              # API client for Flask server
├── app.json                # Expo configuration (PWA settings)
├── package.json
└── README.md               # This file
```

---

## API Endpoints (Flask Server)

The app communicates with the following endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/drones/active` | List active drones |
| POST | `/drones/spawn` | Spawn new drone |
| DELETE | `/drones/{num}` | Remove drone |
| GET | `/zones` | List active zones |
| POST | `/zones` | Create exclusion zone |
| DELETE | `/zones/{id}` | Delete zone |

---

## Demo Workflow (from Issue #2)

Hackathon organizer workflow:

1. Open app on Tablet (web or mobile)
2. **Spawn 2 drones**: Position (5, 5, 0.5) and (10, 0, 0.5)
3. Observe drones appearing in Gazebo simulation
4. **Create "Jamming Zone Alpha"**: Center (15, 10, 0), Radius 20m
5. Watch red cylinder appear in Gazebo
6. **Remove one drone** to simulate fleet reduction
7. **Delete jamming zone** when crisis resolved

Expected reaction: *"Wow, we can modify the simulation in real-time! This is powerful for testing crisis response scenarios."*

---

## Technologies

- **Expo SDK 54** - React Native framework
- **React Native** - Mobile UI framework
- **TypeScript** - Type safety
- **Axios** - HTTP client
- **Metro** - JavaScript bundler (web + mobile)

---

## Known Limitations

- **Max drones**: 10 (configurable in server)
- **Spawn time**: 10-15 seconds (PX4 startup)
- **No auth**: Production deployment should add authentication
- **No WebSocket**: Uses polling for real-time updates (pull-to-refresh)

---

## Future Enhancements

- [ ] WebSocket real-time updates instead of pull-to-refresh
- [ ] Drone status indicators (armed, flying, battery)
- [ ] Gazebo camera view embedded in app
- [ ] Mission waypoint editor
- [ ] Multi-user collaboration (lock zones during editing)
- [ ] Offline mode with queued commands

---

## License

MIT

---

## Support

For issues or questions, contact the Evolutek team or check the main project README.
