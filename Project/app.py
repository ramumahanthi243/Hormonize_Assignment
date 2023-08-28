from flask import Flask, request, jsonify
import requests
import redis
import datetime
import json

app = Flask(__name__)
cache = redis.Redis(host='localhost', port=6379, db=0)

METAR_URL = "http://tgftp.nws.noaa.gov/data/observations/metar/stations/"

def fetch_metar_data(station_code):
    response = requests.get(METAR_URL + f"{station_code}.TXT")
    if response.status_code == 200:
        return response.text
    return None

def parse_metar_data(metar_data):
    lines = metar_data.split('\n')
    # ['2023/08/27 06:35', 'KSGS 270635Z AUTO 08005KT 10SM CLR 16/11 A3017 RMK AO2 T01590113', '']
    observation_datetime = datetime.datetime.strptime(lines[0], "%Y/%m/%d %H:%M")
    details_split = lines[1].split()
    station_code = details_split[0]
    wind_info = details_split[3]
    # visibility = lines[4].split()[0]
    temperature = details_split[6].split("/")[0]
    wind_direction = wind_info[:3]
    wind_speed = wind_info[3:5]
    foriegn_temp = int(temperature) * 9/5 + 32
    parsed_data = {
        'station': station_code,
        'last_observation': observation_datetime.strftime('%Y/%m/%d at %H:%M GMT'),
        'temperature': f'{temperature} C ({foriegn_temp} F)',
        'wind': f'{wind_direction} at {wind_speed} knots'
    }
    return parsed_data

@app.route('/metar/ping')
def ping():
    return jsonify({'data': 'pong'})

@app.route('/metar/info')
def get_metar_info():
    try:
        station_code = request.args.get('scode')
        nocache = request.args.get('nocache', '0') == '1'
        if not station_code:
            return jsonify({'data': 'Requires station code value'}),400
        if nocache:
            data = fetch_metar_data(station_code)
            if data:
                cache.set(station_code, data, ex=300)  # Cache for 5 minutes
        else:
            data = cache.get(station_code)
            if not data:
                data = fetch_metar_data(station_code)
                if data:
                    cache.set(station_code, data, ex=300)  # Cache for 5 minutes
        
        if data:
            parsed_data = parse_metar_data(data)
            return jsonify({'data': parsed_data}), 200
        else:
            return jsonify({'data': 'Error fetching METAR data'}),200
    except Exception as msg:
        return jsonify({'data': str(msg)}), 400

if __name__ == '__main__':
    app.run(host='localhost', port=8080)
