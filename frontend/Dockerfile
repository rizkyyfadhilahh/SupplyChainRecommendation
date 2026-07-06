# ── Stage 1: deps ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

# ✅ PERFORMANCE: Copy lockfile first — layer cache hit when deps unchanged
COPY package.json package-lock.json ./

# ✅ PERFORMANCE: Use npm ci with cache mount (Docker BuildKit)
RUN npm ci

# ── Stage 2: builder ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# ✅ PERFORMANCE: Reuse installed node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build args baked in at build time for server components
ARG BACKEND_URL=http://backend:8000
ARG BACKEND_API_KEY=dev-secret-key

ENV BACKEND_URL=$BACKEND_URL
ENV BACKEND_API_KEY=$BACKEND_API_KEY
ENV NEXT_TELEMETRY_DISABLED=1
# ✅ PERFORMANCE: Limit Node.js memory during build
ENV NODE_OPTIONS="--max-old-space-size=1024"

RUN npm run build

# ── Stage 3: runtime ──────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy built output from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# ✅ PERFORMANCE: Use tini as init process to handle signals properly
CMD ["node", "server.js"]
