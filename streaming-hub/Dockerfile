# --- Build Stage ---
FROM golang:1.24-alpine AS builder

WORKDIR /app

# Install build dependencies for CGO and librdkafka
RUN apk add --no-cache gcc musl-dev pkgconfig

# Only copy go.mod/sum first for better caching
COPY go.mod go.sum ./
RUN go mod download

# Copy the rest of the code
COPY . .

# Build the Go binary (CGO enabled by default)
RUN go build -tags musl -ldflags="-s -w" -o streaming-hub ./cmd/server/main.go

# --- Final Stage ---
FROM alpine:latest

WORKDIR /app

# Install curl for healthchecks
RUN apk add --no-cache curl

# Copy the binary and .env/example.env for local config
COPY --from=builder /app/streaming-hub /app/streaming-hub
COPY --from=builder /app/.env /app/.env
COPY --from=builder /app/.example.env /app/.example.env

# Expose the port your app listens on (e.g., 4001)
EXPOSE 4001

# Start the app
ENTRYPOINT ["/app/streaming-hub"]
