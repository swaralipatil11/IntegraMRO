# Stage 1: Build React assets using Node
FROM node:18-alpine AS build

WORKDIR /app

# Copy package configuration files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code and compile
COPY . .
RUN npm run build

# Stage 2: Serve compiled static files with Nginx
FROM nginx:alpine

# Copy built assets to Nginx html directory
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration if needed (otherwise fallback to default)
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
