# driver_simulator/simulator.py
import os
import requests
import time
import random
import sys

def run_simulator(driver_id, location_service_url):
    """Simulates a driver sending location updates."""
    print(f"Starting simulator for driver_id: {driver_id}")
    while True:
        location_data = {
            "driver_id": driver_id,
            # Simulate coordinates around a central point (e.g., downtown)
           "latitude": round(34.0522 + random.uniform(-0.02, 0.02), 6),
           "longitude": round(-118.2437 + random.uniform(-0.02, 0.02), 6),
        }
        try:
            response = requests.post(
                f"{location_service_url}/update-location",
                json=location_data
            )
            response.raise_for_status()
            print(f"Driver {driver_id}: Location update sent successfully. {location_data}")
        except requests.exceptions.RequestException as e:
            print(f"Driver {driver_id}: Could not send location update: {e}")

        # Wait for a few seconds before the next update
        time.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simulator.py <driver_id>")
        sys.exit(1)

    driver_id = sys.argv[1]
    location_service_url = os.environ.get("LOCATION_SERVICE_URL", "http://localhost:8080")
    
    run_simulator(driver_id, location_service_url)