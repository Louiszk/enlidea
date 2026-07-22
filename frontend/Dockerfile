# Stage 1: Base & Dependencies
FROM node:22-alpine AS base
WORKDIR /app
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm npm ci


# Stage 2: Local Development (HMR & Dev Server)
FROM base AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Stage 3: Production Build
FROM base AS build
ARG VITE_API_BASE_URL
ARG VITE_MCP_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_MCP_URL=$VITE_MCP_URL
COPY . .
RUN npm run build

# Stage 4: Production Serve (Lightweight Nginx serving compiled bundle)
FROM nginx:1.26-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
RUN echo 'server { \
    listen 5173; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf
EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]
