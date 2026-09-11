# syntax=docker/dockerfile:1
#
# Multi-stage: the `node` toolchain (npm, the Vite build) lives only in the build stage.
# The runtime stage is plain nginx serving the static `dist/` output — no node, no npm,
# no source, in the final image.

# ---- build ---------------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN npm run build

# ---- runtime ------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
