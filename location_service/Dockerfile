# location_service/Dockerfile

# ---- Stage 1: Build ----
# Use the official Golang image to build the application.
FROM golang:1.22-alpine as builder

WORKDIR /app

# 1. Copy the module files first. This is still a good practice for layer caching.
# If go.mod/go.sum don't change, this layer is cached.
COPY go.mod go.sum* ./

# 2. Copy the entire source code into the container.
# This is the critical step that was missing in the right place.
COPY . .

# 3. Tidy the modules. NOW, 'go mod tidy' can see your main.go,
# realize it imports go-redis, and correctly populate the go.sum file.
# It will also download the dependencies. This is the fix.
RUN go mod tidy

# 4. Build the application. The go.sum file is now correct, so the build will succeed.
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o /go/bin/location-service .


# ---- Stage 2: Final ----
# Use a minimal 'scratch' image which contains nothing, just our app.
FROM scratch

COPY --from=builder /go/bin/location-service /location-service

# Expose both the application and the metrics ports
EXPOSE 8081
EXPOSE 9091

ENTRYPOINT ["/location-service"]