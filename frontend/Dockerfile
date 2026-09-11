# syntax=docker/dockerfile:1
#
# Multi-stage: the `node` toolchain (npm, the Vite build) lives only in the build stage.
# The runtime stage is plain nginx serving the static `dist/` output — no node, no npm,
# no source, in the final image.
#
# VITE_API_URL is a *build-time* argument: Vite inlines it into the built JS, it is not
# read at container start. That is the Beat 2.2 workaround (bake in a port-forward URL) —
# Beat 2.3 removes it once the SPA and api share one origin.

# ---- build ---------------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---- runtime ------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
