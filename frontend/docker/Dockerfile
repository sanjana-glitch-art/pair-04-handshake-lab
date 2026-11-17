# Pair 4 Handshake - React frontend + nginx API gateway.
# Build from frontend/:  docker build -f docker/Dockerfile -t p4-frontend:2.0 .
FROM node:20-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html ./
COPY src/ src/
# Same-origin API calls through the gateway below.
ENV VITE_API_BASE_URL=/api
RUN npm run build

FROM nginx:1.27-alpine
# Service addresses come from the environment (Compose or a Kubernetes
# ConfigMap); the nginx image renders templates/*.template at start-up.
ENV STUDENT_SERVICE=p4-student-service:9041 \
    COMPANY_SERVICE=p4-company-service:9042 \
    JOB_SERVICE=p4-job-service:9043 \
    APPLICATION_SERVICE=p4-application-service:9044 \
    EVENT_SERVICE=p4-event-service:9045 \
    ASSISTANT_SERVICE=p4-assistant-service:9046 \
    DNS_RESOLVER=127.0.0.11 \
    NGINX_PORT=9040
COPY docker/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 9040
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD wget -qO- http://127.0.0.1:9040/healthz || exit 1
