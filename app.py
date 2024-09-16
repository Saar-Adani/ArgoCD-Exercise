from flask import Flask, render_template, request, redirect, Response
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)

# Directory to store search history
history_dir = 'search_history'
os.makedirs(history_dir, exist_ok=True)

# Set default background color
bg_color = os.getenv('BG_COLOR', '#ffffff')

def get_geocoding_data(city):
    geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
    response = requests.get(geocoding_url)
    if response.status_code != 200:
        return None, f"Error getting geocoding data: {response.status_code} - {response.reason}"
    data = response.json()
    if data.get('results'):
        return data['results'][0], None
    return None, "No results found for the provided city."

def get_weather_data(latitude, longitude):
    weather_url = (f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
                   f"&daily=temperature_2m_max,temperature_2m_min&hourly=relative_humidity_2m&timezone=auto")
    response = requests.get(weather_url)
    if response.status_code != 200:
        return None, f"Error getting weather data: {response.status_code} - {response.reason}"
    return response.json(), None

def calculate_daily_humidity(hourly_humidity):
    daily_humidity = []
    for i in range(0, len(hourly_humidity), 24):
        daily_values = hourly_humidity[i:i + 24]
        average_humidity = round(sum(daily_values) / 24, 2)
        daily_humidity.append(average_humidity)
    return daily_humidity

def process_weather_data(weather_response):
    hourly_humidity = weather_response['hourly']['relative_humidity_2m']
    humidity_list = calculate_daily_humidity(hourly_humidity)

    weather_data = []
    for date, min_temp, max_temp, humidity in zip(weather_response['daily']['time'],
                                                  weather_response['daily']['temperature_2m_min'],
                                                  weather_response['daily']['temperature_2m_max'],
                                                  humidity_list):
        weather_data.append({
            'date': date,
            'min_temp': min_temp,
            'max_temp': max_temp,
            'humidity': humidity
        })
    return weather_data

def save_search_history(city, weather_data):
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    filename = f"{city}_{date_str}.json"
    filepath = os.path.join(history_dir, filename)

    # Load existing data if the file exists
    if os.path.exists(filepath):
        with open(filepath, 'r') as json_file:
            data = json.load(json_file)
    else:
        data = []

    # Append new data
    data.append(weather_data)

    # Save back to the file
    with open(filepath, 'w') as json_file:
        json.dump(data, json_file)

@app.route('/', methods=['GET', 'POST'])
def home():
    global bg_color  # Use the global variable

    weather_data = []
    country = None
    error_message = None
    city_input = None

    if request.method == 'POST':
        if 'city' in request.form:
            city_input = request.form['city']

            geocoding_data, geocoding_error = get_geocoding_data(city_input)
            if geocoding_data:
                country = f"{geocoding_data['name']}, {geocoding_data['country']}"
                weather_response, weather_error = get_weather_data(geocoding_data['latitude'], geocoding_data['longitude'])
                if weather_response:
                    weather_data = process_weather_data(weather_response)
                    save_search_history(city_input, weather_data)  # Save to JSON
                else:
                    error_message = weather_error
            else:
                error_message = geocoding_error
        elif 'bg_color' in request.form:
            # Update background color from the form input
            bg_color = request.form['bg_color']

    return render_template('index.html', weather_data=weather_data, country=country, error_message=error_message, city=city_input, bg_color=bg_color)

@app.route('/history', methods=['GET'])
def history():
    history_files = os.listdir(history_dir)
    return render_template('history.html', history_files=history_files)

@app.route('/download_history/<filename>', methods=['GET'])
def download_history(filename):
    filepath = os.path.join(history_dir, filename)
    if os.path.exists(filepath):
        return Response(
            open(filepath, 'rb').read(),
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'application/json'
            }
        )
    return 'File not found', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0')
