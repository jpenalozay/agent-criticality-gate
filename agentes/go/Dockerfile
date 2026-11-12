FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build
RUN CGO_ENABLED=0 GOOS=linux go build -o api-gateway ./api-gateway

FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy binary
COPY --from=builder /app/api-gateway .

# Expose port
EXPOSE 8080

# Run
CMD ["./api-gateway"]
