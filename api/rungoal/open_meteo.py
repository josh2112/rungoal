from datetime import datetime

import httpx

from rungoal.models import WeatherBase
from rungoal.utils import block_overlap


class OpenMeteoClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        self.metrics = (
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "rain",
            "cloud_cover",
        )
        kwargs.setdefault("base_url", "https://archive-api.open-meteo.com")
        kwargs.setdefault("headers", {"Accept": "application/json"})
        kwargs.setdefault("transport", httpx.HTTPTransport(retries=10))
        super().__init__(*args, **kwargs)

    def fetch_weather(
        self, lat: float, lon: float, start_time: datetime, end_time: datetime
    ) -> WeatherBase:
        response = self.get(
            "/v1/archive",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start_time.date().isoformat(),
                "end_date": end_time.date().isoformat(),
                "hourly": self.metrics,
            },
        )
        response.raise_for_status()

        content = response.json()

        timebase = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        start = (start_time - timebase).total_seconds() / 3600
        end = (end_time - timebase).total_seconds() / 3600

        values = {m: block_overlap(content["hourly"][m], start, end) for m in self.metrics}

        def _get_rounded(name: str, precision: int):
            v = values.get(name)
            return round(v, precision) if v is not None else None

        return WeatherBase(
            temp_c=_get_rounded("temperature_2m", 2),
            apparent_temp_c=_get_rounded("apparent_temperature", 2),
            humidity_pct=_get_rounded("relative_humidity_2m", 0),
            rain_mm=_get_rounded("rain", 0),
            cloud_cover_pct=_get_rounded("cloud_cover", 0),
        )
