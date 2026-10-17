# api_service/app.py
import os
import psycopg2
import psycopg2.extras   # add this line
import pika
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_db_connection():
    """Connects to the PostgreSQL database."""
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST"),
        database=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD")
    )
    return conn

@app.route('/register', methods=['POST'])
def register_user():
    """Registers a new user (rider or driver)."""
    data = request.get_json()   
    user_type = data['type'] # 'rider' or 'driver'
    name = data['name']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, user_type) VALUES (%s, %s) RETURNING id;",
        (name, user_type)
    )
    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": f"{user_type.capitalize()} registered successfully", "user_id": user_id}), 201

@app.route('/request_ride', methods=['POST'])
def request_ride():
    """A rider requests a ride. This is now ASYNCHRONOUS."""
    data = request.get_json()
    rider_id = data['rider_id']

    # 1. Create the trip in the database with 'requested' status
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trips (rider_id, status) VALUES (%s, 'requested') RETURNING id;",
        (rider_id,)
    )
    trip_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    # 2. Publish a message to RabbitMQ
    try:
        rabbitmq_host = os.environ.get("RABBITMQ_HOST")
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
        channel = connection.channel()
        channel.queue_declare(queue='ride_requests', durable=True)
        
        message = {
            'trip_id': trip_id,
            'rider_id': rider_id,
            'latitude': data['latitude'],
            'longitude': data['longitude']
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='ride_requests',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2) # make message persistent
        )
        connection.close()
    except Exception as e:
        # If we can't publish, we should ideally roll back the trip creation or have a retry mechanism
        print(f"Could not publish to RabbitMQ: {e}")
        return jsonify({"error": "Failed to queue ride request"}), 500

    return jsonify({
        "message": "Ride request received. Searching for a driver.",
        "trip_id": trip_id
    }), 202 # 202 Accepted status code is perfect for async operations

@app.route('/trip/<int:trip_id>', methods=['GET'])
def get_trip_status(trip_id):
    """Allows the client to poll for the trip status."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT status, driver_id FROM trips WHERE id = %s", (trip_id,))
    trip = cur.fetchone()
    cur.close()
    conn.close()

    if not trip:
        return jsonify({"error": "Trip not found"}), 404
    
    return jsonify(dict(trip))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)