import requests

class WeatherService:
    @staticmethod
    def get_current_weather(lat, lon):
        """
        Fetches current weather from Open-Meteo API.
        """
        if not lat or not lon:
            return None
            
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true"
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if "current_weather" in data:
                cw = data["current_weather"]
                return {
                    "temperature": cw.get("temperature"),
                    "windspeed": cw.get("windspeed"),
                    "weathercode": cw.get("weathercode"),
                    "condition_text": WeatherService.get_condition_text(cw.get("weathercode"))
                }
        except Exception as e:
            print(f"[ERROR] Weather API failed: {e}")
            return None
        
        return None

    @staticmethod
    def get_rainfall_history(lat, lon):
        """
        Fetches past 5 days of rainfall data.
        """
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "precipitation_sum",
                "past_days": 5,
                "timezone": "auto"
            }
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if "daily" in data:
                return {
                    "dates": data["daily"]["time"],
                    "values": data["daily"]["precipitation_sum"]
                }
        except Exception as e:
            print(f"[ERROR] Rainfall API failed: {e}")
        return None

    @staticmethod
    def get_condition_text(code):
        if code is None: return "Unknown"
        if code == 0: return "Clear sky ☀️"
        if code in [1, 2, 3]: return "Partly cloudy ⛅"
        if code in [45, 48]: return "Foggy 🌫️"
        if code in [51, 53, 55]: return "Drizzle 🌧️"
        if code in [61, 63, 65]: return "Rain 🌧️"
        if code in [71, 73, 75]: return "Snow ❄️"
        if code in [80, 81, 82]: return "Showers 🌦️"
        if code in [95, 96, 99]: return "Thunderstorm ⛈️"
        return "Overcast ☁️"
