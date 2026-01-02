# Multi-stage build for React frontend
FROM node:24-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build arguments for environment variables
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_MOCK_SALESFORCE_URL=http://localhost:8001
ARG VITE_LANGGRAPH_URL=http://localhost:8002

# Set environment variables for build
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_MOCK_SALESFORCE_URL=$VITE_MOCK_SALESFORCE_URL
ENV VITE_LANGGRAPH_URL=$VITE_LANGGRAPH_URL

# Build the application
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Install wget for healthcheck
RUN apk add --no-cache wget

# Copy built files to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

