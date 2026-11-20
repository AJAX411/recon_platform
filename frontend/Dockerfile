# Bases oficiales linux/amd64 verificadas; no requiere frontend externo de build.
ARG NODE_IMAGE=node:26.13.1-bookworm-slim@sha256:18a166e2d50578afe933434857ed2d9059bd1aa398a223e9c89eb4302354f079
ARG NGINX_IMAGE=nginx:1.30.7-alpine@sha256:4d1d4ce08432dc7dfe4af762cb224ce6b5273ae878f41e020ea2425d02ea91a4
FROM ${NODE_IMAGE} AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src/ ./src/
RUN npm run build

FROM ${NGINX_IMAGE} AS runtime
COPY frontend/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/
USER nginx
EXPOSE 8443
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/_frontend_liveness"]
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
