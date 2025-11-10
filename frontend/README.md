# Frontend - Artefac Drone Defense

React + TypeScript web interface for drone control and real-time telemetry monitoring.

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2.0 | UI library |
| TypeScript | 5.3.3 | Type safety |
| Vite | 5.0.8 | Build tool & dev server |
| TailwindCSS | 3.3.6 | Utility-first CSS framework |
| Axios | 1.6.2 | HTTP client for API calls |

## Architecture

### Component Structure

```
src/
├── components/
│   ├── HealthDashboard.tsx   # System health monitoring (all services status)
│   ├── DroneControl.tsx      # Command buttons (ARM/DISARM/TAKEOFF/LAND)
│   └── DroneTelemetry.tsx    # Real-time telemetry display
├── hooks/
│   └── useWebSocket.ts       # WebSocket connection hook
├── utils/
│   └── api.ts                # Backend API client
├── types/
│   └── index.ts              # TypeScript type definitions
├── App.tsx                   # Main app component
└── main.tsx                  # Application entry point
```

### Key Components

#### HealthDashboard
Displays real-time status of all system components:
- MQTT broker connection status
- Database connectivity
- Drone registration status
- Last telemetry update timestamp

```typescript
interface HealthStatus {
  mqtt: 'healthy' | 'unhealthy';
  database: 'healthy' | 'unhealthy';
  drones: {
    id: string;
    status: 'connected' | 'disconnected';
  }[];
}
```

#### DroneControl
Interactive control panel with command buttons:
- ARM/DISARM toggle switch
- TAKEOFF button (with altitude parameter)
- LAND button
- Real-time command result feedback

Features:
- Loading states during command execution
- Success/error message display
- Disabled state when drone is not connected

#### DroneTelemetry
Real-time telemetry display using WebSocket:
- Position (X, Y, Z coordinates)
- Velocity (VX, VY, VZ)
- Battery voltage and percentage
- Armed state and flight mode
- Connection status

Updates automatically via WebSocket at ~1-2Hz

### State Management

Uses React hooks (useState, useEffect) for local component state. No global state management library (like Redux) is used to keep the architecture simple.

Custom hooks:
- `useWebSocket(url)` - Manages WebSocket connection and automatic reconnection

### API Integration

Backend API client (`utils/api.ts`) using Axios:

```typescript
// Base configuration
const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 5000,
});

// Example endpoints
GET  /health              // System health check
GET  /drones              // List all drones
GET  /drones/{id}         // Get drone details
POST /drones/{id}/arm     // Arm drone
POST /drones/{id}/disarm  // Disarm drone
POST /drones/{id}/takeoff // Takeoff with altitude
POST /drones/{id}/land    // Land drone
```

### WebSocket Integration

Real-time telemetry streaming:

```typescript
// Connect to specific drone
const ws = new WebSocket('ws://localhost:8000/ws/drone/drone_1');

// Receive telemetry updates
ws.onmessage = (event) => {
  const telemetry = JSON.parse(event.data);
  // Update UI with new telemetry data
};
```

Message format:
```json
{
  "drone_id": "drone_1",
  "position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "velocity": {"vx": 0.0, "vy": 0.0, "vz": 0.0},
  "battery": {"voltage": 16.8, "remaining": 100},
  "armed": false,
  "mode": "MANUAL",
  "timestamp": "2025-11-10T12:34:56.789Z"
}
```

## Development

### Prerequisites
- Node.js 18+ (required by Vite 5.0)
- npm or yarn package manager

### Local Development

```bash
# Install dependencies
npm install

# Start dev server with HMR (Hot Module Replacement)
npm run dev
# Opens at http://localhost:5173

# Build for production
npm run build
# Output: dist/

# Preview production build locally
npm run preview
```

### Development Workflow

1. **Development Server**: `npm run dev`
   - HMR (instant updates without refresh)
   - TypeScript type checking
   - TailwindCSS compilation
   - Accessible at http://localhost:5173

2. **Backend Connection**: Ensure backend is running
   ```bash
   # In project root
   docker compose up backend
   ```

3. **WebSocket Connection**: Ensure full stack is running
   ```bash
   # In project root
   docker compose up
   ```

### Type Safety

TypeScript provides compile-time type checking:

```typescript
// Type definitions in src/types/index.ts
interface Telemetry {
  drone_id: string;
  position: { x: number; y: number; z: number };
  velocity: { vx: number; vy: number; vz: number };
  battery: { voltage: number; remaining: number };
  armed: boolean;
  mode: string;
  timestamp: string;
}
```

## Docker Deployment

### Multi-Stage Build

The Dockerfile uses multi-stage builds for optimized image size:

```dockerfile
# Stage 1: Build (Node.js 18)
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production (Nginx Alpine)
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**Benefits**:
- Final image size: ~25 MB (vs ~1.5 GB with Node.js included)
- No development dependencies in production
- Fast startup time

### Nginx Configuration

Static file serving with API proxy:

```nginx
server {
  listen 80;

  # React app (SPA routing)
  location / {
    root /usr/share/nginx/html;
    try_files $uri /index.html;  # Fallback to index.html for React Router
  }

  # API proxy (avoid CORS issues)
  location /api/ {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  # WebSocket proxy
  location /ws/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
}
```

### Running with Docker Compose

```bash
# Build and start frontend container
docker compose up frontend

# Access at http://localhost:3000
```

The container:
- Serves static files via Nginx
- Proxies API calls to backend container
- Proxies WebSocket connections
- Automatically restarts on failure

## Styling

### TailwindCSS Utility Classes

Example component with Tailwind:

```tsx
<div className="flex flex-col gap-4 p-6 bg-white rounded-lg shadow-md">
  <h2 className="text-2xl font-bold text-gray-800">Drone Control</h2>
  <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50">
    ARM
  </button>
</div>
```

**Benefits**:
- No CSS files to maintain
- Responsive design with breakpoint prefixes (`md:`, `lg:`)
- Consistent design system
- Tree-shaken in production (only used classes included)

### Color Palette

Status indicators:
- Green (#10B981) - Healthy/Connected/Armed
- Red (#EF4444) - Error/Disconnected/Disarmed
- Yellow (#F59E0B) - Warning/Pending
- Gray (#6B7280) - Disabled/Inactive

## Performance Optimization

### Build Optimizations

Vite automatically applies:
- Code splitting (separate chunks per route)
- Tree shaking (remove unused code)
- Minification (reduce file size)
- Asset optimization (images, fonts)

### Production Bundle Analysis

```bash
npm run build
# Check dist/ folder size
du -sh dist/
```

Typical bundle sizes:
- JavaScript: ~150 KB (gzipped)
- CSS: ~10 KB (gzipped)
- Total initial load: ~160 KB

### Runtime Performance

- React reconciliation optimized with keys
- WebSocket auto-reconnection with exponential backoff
- Debounced telemetry updates (prevent UI thrashing)

## Environment Variables

No environment variables required. API endpoints are hardcoded to backend container name (`http://backend:8000` in Docker, `http://localhost:8000` for local dev).

For custom API URL:

```typescript
// src/utils/api.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

Then set in `.env`:
```bash
VITE_API_URL=http://custom-backend:8000
```

## Troubleshooting

### Issue: WebSocket not connecting

**Symptoms**: Telemetry not updating, "Connection failed" in console

**Solutions**:
1. Ensure backend is running: `docker compose ps backend`
2. Check backend logs: `docker compose logs backend`
3. Verify WebSocket endpoint: `ws://localhost:8000/ws/drone/drone_1`
4. Check browser console for errors

### Issue: API calls failing with CORS

**Symptoms**: `Access-Control-Allow-Origin` error in console

**Solutions**:
1. In Docker: Use Nginx proxy (already configured)
2. For local dev: Start backend with CORS enabled
3. Verify backend CORS middleware configuration

### Issue: Build fails with TypeScript errors

**Symptoms**: `npm run build` fails with type errors

**Solutions**:
1. Run `npm run dev` first to see errors
2. Check `tsconfig.json` configuration
3. Ensure all dependencies have types (`@types/*` packages)
4. Fix type errors in code

### Issue: Blank page after deployment

**Symptoms**: White screen, no errors in console

**Solutions**:
1. Check nginx logs: `docker compose logs frontend`
2. Verify build output exists: `docker exec artefac_frontend ls /usr/share/nginx/html`
3. Check nginx configuration: `docker exec artefac_frontend cat /etc/nginx/conf.d/default.conf`
4. Inspect browser network tab for 404 errors

## Testing

**Current Status**: No tests implemented (hackathon MVP)

**Recommended Testing Stack** (future):
- Jest - Unit testing framework
- React Testing Library - Component testing
- Cypress - End-to-end testing
- MSW (Mock Service Worker) - API mocking

Example test structure:
```typescript
// src/components/__tests__/DroneControl.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import DroneControl from '../DroneControl';

test('ARM button calls api.arm when clicked', async () => {
  render(<DroneControl droneId="drone_1" />);
  const armButton = screen.getByText('ARM');
  fireEvent.click(armButton);
  // Assert API call was made
});
```

## Production Considerations

### Security
- [ ] Add authentication (JWT tokens)
- [ ] Implement HTTPS (TLS certificates)
- [ ] Add CSP (Content Security Policy) headers
- [ ] Sanitize user inputs
- [ ] Add rate limiting on API calls

### Performance
- [ ] Implement service worker (offline support)
- [ ] Add lazy loading for routes
- [ ] Enable gzip/brotli compression in Nginx
- [ ] Add CDN for static assets

### Monitoring
- [ ] Add error tracking (Sentry)
- [ ] Implement analytics (Google Analytics, Plausible)
- [ ] Add performance monitoring (Web Vitals)

### Scalability
- [ ] Implement WebSocket connection pooling
- [ ] Add retry logic with exponential backoff
- [ ] Handle multiple drones in UI
- [ ] Add pagination for drone lists

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Development guidelines
- [README.md](../README.md) - Project overview
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [backend/README.md](../backend/README.md) - Backend API documentation

---

**Last Updated**: 2025-11-10
**Status**: MVP complete with basic control and telemetry ✅
