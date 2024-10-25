from fastapi import FastAPI
import requests
import random
import asyncio

app = FastAPI()

# Thresholds for alerting
TEMP_THRESHOLD = 0.95
WATER_LEVEL_THRESHOLD = 0.96
WATER_FLOW_THRESHOLD = 0.95

# Dummy min and max values for normalization
temp_min, temp_max = 10, 25  # °C
vibration_min, vibration_max = 0.5, 5.0  # Hz
water_level_min, water_level_max = 1.0, 5.0  # meters
water_flow_min, water_flow_max = 50, 200  # m³/s
rainfall_min, rainfall_max = 0, 50  # mm/h
water_pressure_min, water_pressure_max = 1.0, 10.0  # Bar

# List of IoT devices with their locations (near South Lhonak Lake)
iot_devices = [
    {"id": 1, "latitude": 27.865, "longitude": 88.554},  # Top
    {"id": 2, "latitude": 27.864, "longitude": 88.554},
    {"id": 3, "latitude": 27.863, "longitude": 88.555},
    {"id": 4, "latitude": 27.862, "longitude": 88.556},
    {"id": 5, "latitude": 27.861, "longitude": 88.556},
    {"id": 6, "latitude": 27.860, "longitude": 88.557},
    {"id": 7, "latitude": 27.859, "longitude": 88.557},
    {"id": 8, "latitude": 27.858, "longitude": 88.558},
    {"id": 9, "latitude": 27.857, "longitude": 88.559},
    {"id": 10, "latitude": 27.856, "longitude": 88.559},  # Base station
]

# Helper function to normalize sensor data
# Helper function to normalize sensor data and prevent division by zero
def normalize(sensor_value, min_val, max_val):
    if min_val == max_val:
        # In case min and max are the same, normalization doesn't make sense. Return 0.
        return 0.0
    return (sensor_value - min_val) / (max_val - min_val)


# Simulate sensor data
def simulate_sensor_data():
    return {
        "temperature": random.uniform(temp_min, temp_max),
        "vibration": random.uniform(vibration_min, vibration_max),
        "water_level": random.uniform(water_level_min, water_level_max),
        "water_flow": random.uniform(water_flow_min, water_flow_max),
        "rainfall": random.uniform(rainfall_min, rainfall_max),
        "water_pressure": random.uniform(water_pressure_min, water_pressure_max),
    }

# Check if any thresholds are breached
def check_thresholds(sensor_data):
    norm_temp = normalize(sensor_data["temperature"], temp_min, temp_max)
    norm_water_level = normalize(sensor_data["water_level"], water_level_min, water_level_max)
    norm_water_flow = normalize(sensor_data["water_flow"], water_flow_min, water_flow_max)
    
    if norm_temp > TEMP_THRESHOLD or norm_water_level > WATER_LEVEL_THRESHOLD or norm_water_flow > WATER_FLOW_THRESHOLD:
        return True
    return False


async def send_data_to_thingspeak(device, sensor_data):
    API_KEY = "J9WI9QRNLJ7TSU88"
    URL = "https://api.thingspeak.com/update"
    
    # Prepare normalized sensor data
    normalized_data = {
        'temperature': normalize(sensor_data['temperature'], temp_min, temp_max),
        'vibration': normalize(sensor_data['vibration'], vibration_min, vibration_max),
        'water_level': normalize(sensor_data['water_level'], water_level_min, water_level_max),
        'water_flow': normalize(sensor_data['water_flow'], water_flow_min, water_flow_max),
        'rainfall': normalize(sensor_data['rainfall'], rainfall_min, rainfall_max),
        'water_pressure': normalize(sensor_data['water_pressure'], water_pressure_min, water_pressure_max),
    }
    
    # Make the request to ThingSpeak
    response = await asyncio.to_thread(
        requests.get,
        URL,
        params={
            'api_key': API_KEY,
            'field1': normalized_data['temperature'],
            'field2': normalized_data['vibration'],
            'field3': normalized_data['water_level'],
            'field4': normalized_data['water_flow'],
            'field5': normalized_data['rainfall'],
            'field6': normalized_data['water_pressure'],
        }
    )
    
    # Print raw and normalized sensor data
    print(f"Device {device['id']} sent data:")
  
    
    # Highlight any sensors that breached the threshold
    if normalized_data['temperature'] > TEMP_THRESHOLD:
        print(f"Alert: Temperature sensor breached the threshold ({normalized_data['temperature']} > {TEMP_THRESHOLD})")
    if normalized_data['water_level'] > WATER_LEVEL_THRESHOLD:
        print(f"Alert: Water level sensor breached the threshold ({normalized_data['water_level']} > {WATER_LEVEL_THRESHOLD})")
    if normalized_data['water_flow'] > WATER_FLOW_THRESHOLD:
        print(f"Alert: Water flow sensor breached the threshold ({normalized_data['water_flow']} > {WATER_FLOW_THRESHOLD})")


# Trigger flood alert API call (asynchronous)
async def call_flood_api(device):
    API_ENDPOINT = "https://jsonplaceholder.typicode.com/posts"
    data = {
        "device_id": device["id"],
        "latitude": device["latitude"],
        "longitude": device["longitude"],
        "message": "Flood threshold reached",
    }
    response = await asyncio.to_thread(
        requests.post, API_ENDPOINT, json=data
    )
    print(f"API called for Device {device['id']}: {response.status_code} - {response.text}")

# Monitor IoT network in a continuous loop
async def monitor_iot_network():
    while True:
        for device in iot_devices:
            sensor_data = simulate_sensor_data()
            await send_data_to_thingspeak(device, sensor_data)
            
            # Check thresholds
            if check_thresholds(sensor_data):
                print(f"Threshold breached at Device {device['id']}! Calling flood detection API.")
                await call_flood_api(device)
            
            # Simulate a time delay between device checks (non-blocking)
            await asyncio.sleep(5)  # 5-second delay between device checks
            
        # Wait a bit before restarting the loop
        await asyncio.sleep(60)  # 1-minute delay before rechecking all devices

# FastAPI startup event to begin monitoring
@app.on_event("startup")
async def startup_event():
    print("Starting continuous IoT monitoring...")
    asyncio.create_task(monitor_iot_network())  # Start the monitoring task in the background

# FastAPI route for manual alert
@app.post("/manual_alert/")
async def manual_alert(device_id: int):
    device = next((d for d in iot_devices if d["id"] == device_id), None)
    if device:
        print(f"Manual alert triggered for Device {device_id}")
        await call_flood_api(device)
        return {"latitude": device["latitude"], "longitude": device["longitude"]}
    else:
        return {"error": "Device not found"}

