"""Weather engine — seasonal weather rolls and transitions."""

import json

from server.engine.dice import roll
from server.database.connection import fetch_one, execute
from server.config import CONFIG


WEATHER_INTERVAL = CONFIG["world_simulation"]["weather_roll_interval_hours"]


async def roll_weather(season: str) -> dict:
    """Roll d100 and look up the weather for the given season."""
    dice_result = roll("1d100")
    roll_value = dice_result["total"]
    row = await fetch_one(
        "SELECT weather_type, description, effects FROM weather_tables "
        "WHERE season = ? AND d100_min <= ? AND d100_max >= ?",
        (season, roll_value, roll_value),
    )
    if row is None:
        return {
            "roll": roll_value,
            "weather_type": "clear",
            "description": "Clear skies",
            "effects": "",
        }
    return {
        "roll": roll_value,
        "weather_type": row["weather_type"],
        "description": row["description"],
        "effects": row["effects"],
    }


async def update_location_weather(
    location_name: str, weather: dict, current_hour: int
) -> None:
    """Set the weather for a location in world_state."""
    row = await fetch_one(
        "SELECT weather_by_location FROM world_state WHERE id = 1"
    )
    weather_map = json.loads(row["weather_by_location"]) if row["weather_by_location"] else {}
    weather_map[location_name] = {
        "type": weather["weather_type"],
        "description": weather["description"],
        "since_hour": current_hour,
    }
    await execute(
        "UPDATE world_state SET weather_by_location = ? WHERE id = 1",
        (json.dumps(weather_map),),
    )


async def get_current_weather(location_name: str) -> dict | None:
    """Read the current weather for a location from world_state."""
    row = await fetch_one(
        "SELECT weather_by_location FROM world_state WHERE id = 1"
    )
    weather_map = json.loads(row["weather_by_location"]) if row["weather_by_location"] else {}
    return weather_map.get(location_name)


async def check_weather_transition(
    location_name: str, current_hour: int, season: str
) -> dict | None:
    """Roll new weather if enough time has passed since the last change."""
    current = await get_current_weather(location_name)
    if current is not None:
        elapsed = current_hour - current["since_hour"]
        if elapsed < WEATHER_INTERVAL:
            return None

    weather = await roll_weather(season)
    await update_location_weather(location_name, weather, current_hour)
    return weather
