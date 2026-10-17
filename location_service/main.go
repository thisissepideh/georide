// location_service/main.go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/redis/go-redis/v9"
)

var ctx = context.Background()
var rdb *redis.Client

const driverLocationsKey = "driver_locations"

// --- Prometheus Metrics ---
var (
	httpRequestsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "http_requests_total",
		Help: "Total number of HTTP requests.",
	}, []string{"path"})

	httpRequestsDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "http_request_duration_seconds",
		Help: "Duration of HTTP requests.",
	}, []string{"path"})
)

type LocationUpdate struct {
	DriverID  string  `json:"driver_id"`
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
}

func initRedis() {
	redisAddr := os.Getenv("REDIS_ADDR")
	if redisAddr == "" {
		redisAddr = "localhost:6379"
	}
	rdb = redis.NewClient(&redis.Options{
		Addr: redisAddr,
	})
	// Ping the server to check the connection
	if _, err := rdb.Ping(ctx).Result(); err != nil {
		log.Fatalf("Could not connect to Redis: %v", err)
	}
	log.Println("Successfully connected to Redis.")
}

func prometheusMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		duration := time.Since(start).Seconds()
		
		httpRequestsTotal.WithLabelValues(r.URL.Path).Inc()
		httpRequestsDuration.WithLabelValues(r.URL.Path).Observe(duration)
	})
}

func updateLocationHandler(w http.ResponseWriter, r *http.Request) {
	var loc LocationUpdate
	if err := json.NewDecoder(r.Body).Decode(&loc); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// GEOADD stores the longitude, latitude, and member name (driver_id)
	err := rdb.GeoAdd(ctx, driverLocationsKey, &redis.GeoLocation{
		Name:      loc.DriverID,
		Longitude: loc.Longitude,
		Latitude:  loc.Latitude,
	}).Err()

	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "Location updated for driver %s", loc.DriverID)
}

func findNearestDriverHandler(w http.ResponseWriter, r *http.Request) {
	lat, err := strconv.ParseFloat(r.URL.Query().Get("latitude"), 64)
	if err != nil {
		http.Error(w, "Invalid latitude", http.StatusBadRequest)
		return
	}
	lon, err := strconv.ParseFloat(r.URL.Query().Get("longitude"), 64)
	if err != nil {
		http.Error(w, "Invalid longitude", http.StatusBadRequest)
		return
	}

	// GeoSearch finds members within a radius of a given point
	locations, err := rdb.GeoSearch(ctx, driverLocationsKey, &redis.GeoSearchQuery{
		Longitude:  lon,
		Latitude:   lat,
		Radius:     5, // Search within a 5 km radius
		RadiusUnit: "km",
		Sort:       "ASC", // Sort by distance ascending
		Count:      1,     // Return only the closest one
	}).Result()

	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	if len(locations) == 0 {
		json.NewEncoder(w).Encode(map[string]interface{}{})
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"driver_id": locations[0],
	})
}

func main() {
	initRedis()

	// Application Server
	appMux := http.NewServeMux()
	appMux.HandleFunc("/update-location", updateLocationHandler)
	appMux.HandleFunc("/find-nearest-driver", findNearestDriverHandler)

	// Metrics Server
	metricsMux := http.NewServeMux()
	metricsMux.Handle("/metrics", promhttp.Handler())

	// Start metrics server in a separate goroutine
	go func() {
		log.Println("Metrics server starting on port 9091...")
		if err := http.ListenAndServe(":9091", metricsMux); err != nil {
			log.Fatalf("Metrics server failed: %v", err)
		}
	}()

	// Start application server with middleware
	log.Println("Application server starting on port 8081...")
	if err := http.ListenAndServe(":8081", prometheusMiddleware(appMux)); err != nil {
		log.Fatalf("Application server failed: %v", err)
	}
}