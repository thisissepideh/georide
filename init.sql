-- init.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    user_type VARCHAR(10) NOT NULL CHECK (user_type IN ('driver', 'rider')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trips (
    id SERIAL PRIMARY KEY,
    rider_id INTEGER REFERENCES users(id),
    driver_id INTEGER REFERENCES users(id),
    status VARCHAR(20) NOT NULL CHECK (status IN ('requested', 'assigned', 'in_progress', 'completed', 'cancelled')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Pre-populate with a few drivers for simulation
INSERT INTO users (name, user_type) VALUES ('Driver-Alpha', 'driver');
INSERT INTO users (name, user_type) VALUES ('Driver-Bravo', 'driver');
INSERT INTO users (name, user_type) VALUES ('Driver-Charlie', 'driver');