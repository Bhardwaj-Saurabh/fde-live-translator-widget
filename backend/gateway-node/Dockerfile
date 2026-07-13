# Build context is the ASSIGNMENT ROOT (fly.gateway.toml lives there) —
# needed because server.js serves the widget from ../../widget/.
FROM node:22-slim

# Keep the repo's relative layout so __dirname/../../widget resolves unchanged
WORKDIR /app/backend/gateway-node

COPY backend/gateway-node/package*.json ./
RUN npm ci --omit=dev 2>/dev/null || npm install --omit=dev

COPY backend/gateway-node/ ./
COPY widget/ /app/widget/

EXPOSE 8787
CMD ["node", "server.js"]
