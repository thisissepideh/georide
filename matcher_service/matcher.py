# matcher_service/matcher.py
import os
import pika
import json
import time
import requests
import psycopg2

# --- Database Connection ---
def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST"),
        database=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD")
    )
    return conn

# --- Driver lookup with retries ---
FIND_ATTEMPTS = 5
FIND_DELAY_SECONDS = 2

def find_driver_with_retry(latitude, longitude):
    location_service_url = os.environ.get("LOCATION_SERVICE_URL")
    for attempt in range(1, FIND_ATTEMPTS + 1):
        response = requests.get(
            f"{location_service_url}/find-nearest-driver",
            params={"latitude": latitude, "longitude": longitude},
            timeout=5,
        )
        response.raise_for_status()
        driver_info = response.json()
        if driver_info and 'driver_id' in driver_info:
            print(f"[*] Found nearest driver: {driver_info['driver_id']} (attempt {attempt})")
            return driver_info['driver_id']
        print(f" [~] No driver nearby (attempt {attempt}/{FIND_ATTEMPTS})", flush=True)
        if attempt < FIND_ATTEMPTS:
            time.sleep(FIND_DELAY_SECONDS)
    return None

# --- Callback for RabbitMQ ---
def on_ride_request(ch, method, properties, body):
    data = json.loads(body)
    print(f" [x] Received ride request: {data}")

    rider_id = data['rider_id']
    latitude = data['latitude']
    longitude = data['longitude']
    trip_id = data['trip_id']

    # 1. Find nearest driver via Location Service (retry a few times)
    try:
        driver_id = find_driver_with_retry(latitude, longitude)
    except requests.exceptions.RequestException as e:
        print(f" [!] Could not connect to location service: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    # 2. If driver found, update the trip in PostgreSQL
    if driver_id:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # We need the real user ID of the driver from the users table
            cur.execute("SELECT id FROM users WHERE name = %s AND user_type = 'driver';", (driver_id,))
            driver_user_id = cur.fetchone()[0]

            cur.execute(
                "UPDATE trips SET driver_id = %s, status = 'assigned' WHERE id = %s;",
                (driver_user_id, trip_id)
            )
            conn.commit()
            cur.close()
            conn.close()
            print(f"[*] Successfully assigned driver {driver_id} (ID: {driver_user_id}) to trip {trip_id}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f" [!] Database error: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True) # Requeue on DB error
    else:
        print(f" [!] No driver found for trip {trip_id}. Marking as cancelled.")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE trips SET status = 'cancelled' WHERE id = %s;", (trip_id,))
        conn.commit()
        cur.close()
        conn.close()
        ch.basic_ack(delivery_tag=method.delivery_tag)

# --- Main Loop ---
def main():
    rabbitmq_host = os.environ.get("RABBITMQ_HOST")

    # Retry until RabbitMQ is ready
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=rabbitmq_host, heartbeat=600)
            )
            break
        except pika.exceptions.AMQPConnectionError:
            print(" [!] RabbitMQ not ready, retrying in 5s...", flush=True)
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue='ride_requests', durable=True)
    channel.basic_consume(queue='ride_requests', on_message_callback=on_ride_request)
    print(' [*] Waiting for ride requests. To exit press CTRL+C', flush=True)
    channel.start_consuming()

if __name__ == '__main__':
    main()