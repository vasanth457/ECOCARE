# --- FILE: plantcare.py ---
"""
Plantcare module for ECO CARE.
Provides weather-driven irrigation schedules and monitoring.
"""

from weather_module import (
    STATES_DISTRICTS,
    ALL_STATES,
    get_weather_svg,
    render_weather_icon,
    get_demo_weather_sirkazhi,
    get_weather_realtime,
    get_plant_watering_advice,
    render_weather_html_card,
    render_plant_watering_card,
    weather_monitoring_page
)

# Backward-compatibility alias
def show_plantcare(default_city: str = "Sirkazhi"):
    """Legacy entrypoint redirected to the pixel-perfect real-time weather monitoring system."""
    weather_monitoring_page()
