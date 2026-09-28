# syntax=docker/dockerfile:1
FROM node:22-alpine AS builder

WORKDIR /app

# Dependencies before source: this layer only invalidates when package*.json changes.
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:1.27-alpine

# The base image's Alpine OS packages (libxml2, musl, nghttp2, zlib) lag behind
# upstream security patches within the same nginx:1.27-alpine tag — apk upgrade pulls the
# current patched versions from the pinned Alpine release's own repos, without moving off
# the pinned nginx minor version.
RUN apk --no-cache upgrade

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx normally creates its temp dirs lazily as root before dropping
# privileges; since we run as `nginx` from the start (no root step), create
# and own them ourselves. Pid file also moves to world-writable /tmp.
RUN mkdir -p /var/cache/nginx/client_temp /var/cache/nginx/proxy_temp \
        /var/cache/nginx/fastcgi_temp /var/cache/nginx/uwsgi_temp /var/cache/nginx/scgi_temp \
    && chown -R nginx:nginx /var/cache/nginx \
    && sed -i -e 's#^user  *nginx;##' -e 's#pid *\/run/nginx.pid;#pid /tmp/nginx.pid;#' \
        /etc/nginx/nginx.conf

USER nginx
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://localhost:8080/healthz"]

CMD ["nginx", "-g", "daemon off;"]
