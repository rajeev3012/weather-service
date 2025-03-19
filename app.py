from flask import Flask, jsonify
import os
import time
import logging
import random
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY

# -------------------------------
# Initialize the Flask application
# -------------------------------
app = Flask(__name__)

# -------------------------------
# Configure logging for debugging and monitoring
# -------------------------------
logging.basicConfig(
    level=logging.INFO,  # Set logging level to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'  # Log message format
)
logger = logging.getLogger(__name__)

# -------------------------------
# Define Prometheus metrics for monitoring endpoints
# -------------------------------
REQUEST_COUNT = Counter(
    'weather_request_count', 
    'Total number of weather requests', 
    ['endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'weather_request_latency_seconds', 
    'Request latency in seconds', 
    ['endpoint']
)

# -------------------------------
# Define mock weather data with dynamic values using lambda functions
# -------------------------------
WEATHER_DATA = {
    "new_york": {
        "city": "New York",
        "temperature": lambda: random.uniform(0, 35),
        "conditions": lambda: random.choice(["Sunny", "Cloudy", "Rainy", "Snowy"]),
        "humidity": lambda: random.uniform(30, 90),
    },
    "london": {
        "city": "London",
        "temperature": lambda: random.uniform(-5, 25),
        "conditions": lambda: random.choice(["Cloudy", "Rainy", "Foggy", "Clear"]),
        "humidity": lambda: random.uniform(40, 95),
    },
}

# -------------------------------
# Health check endpoint for Kubernetes liveness probe
# -------------------------------
@app.route('/health', methods=['GET'])
def health_check():
    # Returns a JSON response indicating the service is healthy
    return jsonify({"status": "healthy"}), 200

# -------------------------------
# Metrics endpoint for Prometheus to collect metrics
# -------------------------------
@app.route('/metrics', methods=['GET'])
def metrics():
    # Generate the latest metrics data and return it with plain text content type
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain'}

# -------------------------------
# Weather endpoint to retrieve weather data for a specific city
# -------------------------------
@app.route('/weather/<city>', methods=['GET'])
def get_weather(city):
    start_time = time.time()  # Start timer to measure request latency
    
    try:
        # Check if the city exists in the weather data. Cities are case insensitive.
        if city.lower() not in WEATHER_DATA:
            logger.warning(f"Weather request for unknown city: {city}")
            REQUEST_COUNT.labels(endpoint='/weather', status='404').inc()  # Increment 404 counter
            response = jsonify({"error": f"City {city} not found"}), 404
        else:
            # Retrieve and generate dynamic weather data
            city_data = WEATHER_DATA[city.lower()]
            weather = {
                "city": city_data["city"],
                "temperature": round(city_data["temperature"](), 1),  # Generate temperature and round it
                "conditions": city_data["conditions"](),  # Select random weather condition
                "humidity": round(city_data["humidity"](), 1),  # Generate humidity and round it
                "timestamp": time.time()
            }
            logger.info(f"Weather request successful for: {city}")
            REQUEST_COUNT.labels(endpoint='/weather', status='200').inc()  # Increment 200 counter
            response = jsonify(weather), 200
    except Exception as e:
        # Log any errors and return a 500 error code
        logger.error(f"Error processing weather request: {str(e)}")
        REQUEST_COUNT.labels(endpoint='/weather', status='500').inc()
        response = jsonify({"error": "Internal server error"}), 500
    
    # Record the request latency using the Histogram metric
    REQUEST_LATENCY.labels(endpoint='/weather').observe(time.time() - start_time)
    return response

# -------------------------------
# Root endpoint providing service information
# -------------------------------
@app.route('/', methods=['GET'])
def index():
    # Return service details, version and available endpoints
    return jsonify({
        "service": "Weather Microservice",
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Service information"},
            {"path": "/health", "method": "GET", "description": "Health check endpoint"},
            {"path": "/metrics", "method": "GET", "description": "Prometheus metrics"},
            {"path": "/weather/<city>", "method": "GET", "description": "Get weather for a city"}
        ]
    })

# -------------------------------
# Run the Flask application
# -------------------------------
if __name__ == '__main__':
    # Get port from environment variable or fall back to default port 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)