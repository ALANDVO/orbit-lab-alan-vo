FROM node:24-alpine AS builder

WORKDIR /src

# Install dependencies (locked)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Copy source
COPY frontend/src ./src
COPY frontend/index.html ./

# Build
RUN npm run build

# Production stage — serve with a lightweight static server
FROM node:24-alpine AS runtime

WORKDIR /app

# Create nonroot user
RUN addgroup -S orbitlab && adduser -S -G orbitlab orbitlab

# Install only production dependencies (vite preview as static server)
RUN npm install -g serve@14.2.3

# Copy built files
COPY --from=builder /src/dist ./dist

USER orbitlab

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://127.0.0.1:3000/',r=>process.exit(r&&r.statusCode===200?0:1)).on('error',()=>process.exit(1))" || exit 1

CMD ["serve", "-s", "dist", "-l", "tcp://0.0.0.0:3000"]