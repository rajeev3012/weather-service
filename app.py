from flask import Flask, jsonify
import os
import time
import logging
import random
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY

# Set up Flask application
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define Prometheus metrics
REQUEST_COUNT = Counter('weather_request_count', 'Total number of weather requests', ['endpoint', 'status'])
REQUEST_LATENCY = Histogram('weather_request_latency_seconds', 'Request latency in seconds', ['endpoint'])

# Mock weather data for different cities
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
    "tokyo": {
        "city": "Tokyo",
        "temperature": lambda: random.uniform(5, 35),
        "conditions": lambda: random.choice(["Clear", "Cloudy", "Rainy", "Stormy"]),
        "humidity": lambda: random.uniform(30, 85),
    }
}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Kubernetes liveness probe"""
    return jsonify({"status": "healthy"}), 200

@app.route('/metrics', methods=['GET'])
def metrics():
    """Endpoint for Prometheus metrics collection"""
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain'}

@app.route('/weather/<city>', methods=['GET'])
def get_weather(city):
    """Endpoint to retrieve weather data for a specific city"""
    start_time = time.time()
    
    try:
        # Check if city exists in our data
        if city.lower() not in WEATHER_DATA:
            logger.warning(f"Weather request for unknown city: {city}")
            REQUEST_COUNT.labels(endpoint='/weather', status='404').inc()
            response = jsonify({"error": f"City {city} not found"}), 404
        else:
            # Generate dynamic weather data
            city_data = WEATHER_DATA[city.lower()]
            weather = {
                "city": city_data["city"],
                "temperature": round(city_data["temperature"](), 1),
                "conditions": city_data["conditions"](),
                "humidity": round(city_data["humidity"](), 1),
                "timestamp": time.time()
            }
            logger.info(f"Weather request successful for: {city}")
            REQUEST_COUNT.labels(endpoint='/weather', status='200').inc()
            response = jsonify(weather), 200
    except Exception as e:
        logger.error(f"Error processing weather request: {str(e)}")
        REQUEST_COUNT.labels(endpoint='/weather', status='500').inc()
        response = jsonify({"error": "Internal server error"}), 500
    
    # Record request latency
    REQUEST_LATENCY.labels(endpoint='/weather').observe(time.time() - start_time)
    return response

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with service information"""
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

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)