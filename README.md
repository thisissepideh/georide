curl -X POST http://localhost/register \
-H "Content-Type: application/json" \
-d '{"name": "Carlos", "type": "rider"}'

# Expected Output: {"message":"Rider registered successfully","user_id":5}

curl -X POST http://localhost/request_ride \
-H "Content-Type: application/json" \
-d '{"rider_id": 5, "latitude": 34.05, "longitude": -118.24}'

# Expected Output (Instant!): {"message":"Ride request received. Searching for a driver.","trip_id":2}

docker-compose logs -f matcher
# You will see logs like: "[x] Received ride request...", "[*] Found nearest driver...", "[*] Successfully assigned driver..."

# Wait a few seconds, then check:
curl http://localhost/trip/2

# Initial Output might be: {"driver_id":null,"status":"requested"}
# Final Output should be: {"driver_id":1,"status":"assigned"} (driver_id will vary)