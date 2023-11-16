# Applifting Marketplace

A simple Web API for creating Products and fetching their Offers from another Microservice. It contains CRUD for Products and ReadOnly endpoints for Offers. Offers for each Product are fetched from specified URL every 90 seconds (you can change the interval in projects settings.py).

The services include a Django web server, a PostgreSQL database, RabbitMQ for message queuing, a Celery worker, and Celery beat for periodic tasks.

## Installation

1) Ensure Docker is installed
2) Create a .env file in the same directory as the Docker Compose file, and set the required environment variables:
   - SECRET_KEY: Django Secret Key
   - OFFERS_SERVICE_BASE_URL: Base URL for Offers Microservice
   - OFFERS_SERVICE_REFRESH_TOKEN: Refresh Token generated using Offers Microservice /auth/ endpoint
   - FETCH_OFFERS_INTERVAL: Interval (seconds) in which will Offers be fetched from Microservice
3) Run docker-compose up to start the services.

```bash
docker-compose up -d
```
## Usage

Swagger API Documentation is available at
```
http://localhost:8000/api/docs/
```
First generate you Access-Token using Auth endpoint:
```
http://localhost:8000/api/v1/auth
```
Include generated Access-Token in Request Headers as Authentication