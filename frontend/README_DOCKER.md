# Frontend Docker Deployment

## Overview

The frontend is containerized using a multi-stage Docker build:
1. **Builder stage**: Uses Node.js to build the React application
2. **Production stage**: Uses nginx to serve the static files

## Building and Running

### Using Docker Compose (Recommended)

The frontend is included in the main `docker-compose.yml`:

```bash
# Build and start all services including frontend
docker-compose up -d --build

# Access the frontend at http://localhost:3000
```

### Building Manually

```bash
# Build the image
docker build -t sfd-clm-frontend ./frontend

# Run the container
docker run -p 3000:80 sfd-clm-frontend
```

## Environment Variables

Environment variables are set at **build time** (not runtime) because Vite embeds them in the JavaScript bundle.

### Default Values

- `VITE_API_BASE_URL=http://localhost:8000` - Backend MCP API
- `VITE_MOCK_SALESFORCE_URL=http://localhost:8001` - Mock Salesforce API
- `VITE_LANGGRAPH_URL=http://localhost:8002` - LangGraph API

### Customizing URLs

To use different URLs, modify the `build.args` section in `docker-compose.yml`:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
    args:
      - VITE_API_BASE_URL=http://your-backend:8000
      - VITE_MOCK_SALESFORCE_URL=http://your-salesforce:8001
      - VITE_LANGGRAPH_URL=http://your-langgraph:8002
```

Then rebuild:

```bash
docker-compose build frontend
docker-compose up -d frontend
```

## Architecture

### Why localhost URLs?

The frontend runs in the **browser** (client-side), not in the Docker container. When the browser makes API requests, it uses the host machine's network, not Docker's internal network. Therefore:

- ✅ Use `http://localhost:8000` (exposed on host machine)
- ❌ Don't use `http://backend-mcp:8000` (Docker internal network, not accessible from browser)

### Network Flow

```
Browser (localhost:3000)
  ↓ HTTP request
Host Machine (localhost:8000)
  ↓ Docker port mapping
Container (backend-mcp:8000)
```

## Development vs Production

### Development (npm run dev)

- Runs Vite dev server on port 5173
- Hot module replacement enabled
- Uses environment variables from `.env` file

### Production (Docker)

- Builds static files with `npm run build`
- Serves with nginx on port 80
- Environment variables baked into build
- Optimized for performance (gzip, caching)

## Troubleshooting

### API requests failing

1. Check backend services are running:
   ```bash
   docker-compose ps
   ```

2. Verify ports are exposed:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   ```

3. Check browser console for CORS errors
4. Verify environment variables in built bundle (check Network tab in DevTools)

### Frontend not loading

1. Check nginx is running:
   ```bash
   docker-compose logs frontend
   ```

2. Verify healthcheck:
   ```bash
   docker-compose ps frontend
   ```

3. Check nginx configuration:
   ```bash
   docker-compose exec frontend cat /etc/nginx/conf.d/default.conf
   ```

### Rebuilding after code changes

```bash
# Rebuild frontend only
docker-compose build frontend

# Restart frontend
docker-compose up -d frontend
```

## Health Check

The frontend includes a healthcheck that verifies nginx is serving content:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --quiet --tries=1 --spider http://localhost/ || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

## Performance Optimizations

The nginx configuration includes:

- **Gzip compression** for text-based assets
- **Long-term caching** for static assets (JS, CSS, images)
- **Client-side routing support** (React Router)
- **Security headers** (X-Frame-Options, X-Content-Type-Options, etc.)

