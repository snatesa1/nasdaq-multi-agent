# ==============================================================================
# Multi-Stage Dockerfile for OptionsLab Frontend (Next.js 14 Static Export)
# ==============================================================================

# Stage 1: Build the static Next.js export
FROM node:20-alpine AS builder
WORKDIR /app

# Install build dependencies
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy source code and build static export
COPY . .
RUN npm run build

# Stage 2: Serve static HTML with ultra-lightweight Nginx (~25MB image)
FROM nginx:alpine
WORKDIR /usr/share/nginx/html

# Clean default nginx files and copy compiled export
RUN rm -rf ./*
COPY --from=builder /app/out ./

# Custom nginx configuration with SPA routing and API reverse-proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
