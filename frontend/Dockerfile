# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --ignore-scripts

# Copy application code
COPY . .

# Build arguments for Next.js public environment variables
# These are embedded at build time
ARG NEXT_PUBLIC_AZURE_AD_CLIENT_ID
ARG NEXT_PUBLIC_AZURE_AD_TENANT_ID
ARG NEXT_PUBLIC_AUTH_ENABLED=true
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_APPINSIGHTS_CONNECTION_STRING
ARG AGENT_API_BASE_URL
ENV NEXT_PUBLIC_AZURE_AD_CLIENT_ID=$NEXT_PUBLIC_AZURE_AD_CLIENT_ID
ENV NEXT_PUBLIC_AZURE_AD_TENANT_ID=$NEXT_PUBLIC_AZURE_AD_TENANT_ID
ENV NEXT_PUBLIC_AUTH_ENABLED=$NEXT_PUBLIC_AUTH_ENABLED
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_APPINSIGHTS_CONNECTION_STRING=$NEXT_PUBLIC_APPINSIGHTS_CONNECTION_STRING
ENV AGENT_API_BASE_URL=$AGENT_API_BASE_URL

# Build the Next.js application
RUN npm run build

# Runtime stage
FROM node:20-alpine

WORKDIR /app

# Copy built application from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000

# Server-side environment variables (can be overridden at runtime)
# AGENT_API_BASE_URL is used by the Next.js API route to proxy requests to the agent
ARG AGENT_API_BASE_URL
ENV AGENT_API_BASE_URL=$AGENT_API_BASE_URL

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Run the application
CMD ["npm", "start"]
