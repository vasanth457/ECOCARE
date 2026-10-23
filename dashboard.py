"""EcoCare's plant-care dashboard and reusable urban plant library."""

import calendar as calendar_module
import base64
import html
import json
import re
import uuid
from io import BytesIO
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image
import streamlit as st
from weather_module import get_weather_realtime


CATALOG_PATH = Path(__file__).with_name("urban_plants.json")
with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
    PLANT_CATALOG = json.load(catalog_file)

PLANTS_BY_NAME = {plant["name"]: plant for plant in PLANT_CATALOG}
STARTER_PLANTS = [
    ("Snake Plant", 2),
    ("Money Plant", 1),
    ("Peace Lily", 3),
    ("Aloe Vera", 4),
    ("Spider Plant", 2),
    ("Lavender", 5),
]


def _safe(value):
    return html.escape(str(value), quote=True)


def _image(plant, css_class=""):
    image_data = plant.get("image_data")
    if image_data:
        if isinstance(image_data, str):
            image_data = image_data.encode("ascii")
        image_url = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('ascii')}"
    else:
        image_url = plant.get("image_url", "")
    if not image_url:
        return (
            f'<div class="{_safe(css_class)} eco-image-placeholder" '
            f'role="img" aria-label="{_safe(plant["name"])}">🌿</div>'
        )
    return (
        f'<img class="{_safe(css_class)}" src="{_safe(image_url)}" '
        f'alt="{_safe(plant["name"])}" loading="lazy">'
    )


def _managed_plants_for_storage(plants):
    stored_plants = []
    for plant in plants:
        saved = {
            "name": plant["name"],
            "last_watered_at": plant["last_watered_at"].isoformat(),
        }
        if plant.get("custom_plant_id"):
            saved["custom_plant_id"] = plant["custom_plant_id"]
        stored_plants.append(saved)
    return stored_plants


def _persist_managed_plants(db, plants):
    user_id = st.session_state.get("user_uid")
    if not user_id:
        raise RuntimeError("Cannot save plant care data without an authenticated user.")
    db.collection("users").document(user_id).set(
        {"managed_plants": _managed_plants_for_storage(plants)},
        merge=True,
    )


def _init_managed_plants(db):
    user_id = st.session_state.get("user_uid")
    if not user_id:
        raise RuntimeError("Cannot load plant care data without an authenticated user.")
    if st.session_state.get("ecocare_loaded_user_uid") == user_id:
        return

    user_ref = db.collection("users").document(user_id)
    user_data = user_ref.get(field_paths=["managed_plants"]).to_dict() or {}
    saved_plants = user_data.get("managed_plants")
    custom_plants = {}
    for custom_plant_doc in user_ref.collection("custom_plants").stream():
        custom_plant_data = custom_plant_doc.to_dict() or {}
        custom_plant_data["custom_plant_id"] = custom_plant_doc.id
        custom_plant_data.pop("photo_credit", None)
        custom_plants[custom_plant_doc.id] = custom_plant_data
    if saved_plants is None:
        plants = [
            {
                **PLANTS_BY_NAME[name],
                "last_watered_at": datetime.now() - timedelta(days=days),
            }
            for name, days in STARTER_PLANTS
        ]
        _persist_managed_plants(db, plants)
    else:
        plants = []
        for saved_plant in saved_plants:
            name = saved_plant["name"]
            custom_plant_id = saved_plant.get("custom_plant_id")
            if custom_plant_id:
                catalog_plant = custom_plants.get(custom_plant_id)
                if catalog_plant is None:
                    raise ValueError(f"Saved custom plant is missing: {name}")
            elif name in PLANTS_BY_NAME:
                catalog_plant = PLANTS_BY_NAME[name]
            else:
                raise ValueError(f"Saved plant is missing from the catalog: {name}")
            plants.append({
                **catalog_plant,
                "last_watered_at": datetime.fromisoformat(saved_plant["last_watered_at"]),
            })

    recent_events_start = (date.today() - timedelta(days=6)).isoformat()
    watering_log = [
        event.to_dict()
        for event in user_ref.collection("watering_events")
        .where("watered_at", ">=", recent_events_start)
        .stream()
    ]
    watering_log.sort(key=lambda event: event["watered_at"])
    st.session_state.ecocare_managed_plants = plants
    st.session_state.ecocare_watering_log = watering_log
    st.session_state.ecocare_loaded_user_uid = user_id


def _search_query(local_key):
    return st.session_state.get(local_key, "").strip().casefold()


@st.cache_data(ttl=300, show_spinner=False)
def _get_live_weather(city, state):
    return get_weather_realtime(city, state)


def _profile_place():
    location = st.session_state.get("user", {}).get("location", "Chennai, Tamil Nadu")
    pieces = [piece.strip() for piece in location.split(",", 1)]
    return (pieces[0] or "Chennai", pieces[1] if len(pieces) > 1 else "Tamil Nadu")


def _days_since_watered(plant, now=None):
    now = now or datetime.now()
    watered_at = plant.get("last_watered_at")
    if isinstance(watered_at, str):
        watered_at = datetime.fromisoformat(watered_at)
    if not isinstance(watered_at, datetime):
        return max(0, int(plant.get("last_watered", 0)))
    return max(0, (now.date() - watered_at.date()).days)


def _watering_interval_days(plant):
    frequency = plant["water_frequency"].casefold()
    if "daily" in frequency:
        return 1
    times = re.search(r"(\d+)(?:-(\d+))?\s*times?\s*per\s*week", frequency)
    if times:
        per_week = int(times.group(2) or times.group(1))
        return max(1, round(7 / per_week))
    every = re.search(r"every\s+(\d+)(?:-(\d+))?\s*(day|week)", frequency)
    if every:
        interval = int(every.group(2) or every.group(1))
        return interval * (7 if every.group(3) == "week" else 1)
    if "weekly" in frequency:
        return 7
    return 7


def _plant_care_status(plant, now=None):
    days_since_watered = _days_since_watered(plant, now)
    interval = _watering_interval_days(plant)
    ratio = days_since_watered / interval
    if ratio <= 0.5:
        return "Excellent"
    if ratio <= 1:
        return "Good"
    if ratio <= 1.5:
        return "Fair"
    return "Needs Attention"


def _plants_for_query(plants, query):
    if not query:
        return plants
    return [
        plant for plant in plants
        if query in plant["name"].casefold()
        or query in plant["scientific_name"].casefold()
        or query in plant["description"].casefold()
    ]


def _custom_plants_in_collection():
    return [
        plant
        for plant in st.session_state.get("ecocare_managed_plants", [])
        if plant.get("custom_plant_id")
    ]


def _add_plant_to_collection(plant_name, db):
    if plant_name not in PLANTS_BY_NAME:
        raise ValueError(f"Unknown plant in catalog: {plant_name}")
    if any(
        plant["name"].casefold() == plant_name.casefold()
        for plant in st.session_state.ecocare_managed_plants
    ):
        return
    plants = [
        *st.session_state.ecocare_managed_plants,
        {**PLANTS_BY_NAME[plant_name], "last_watered_at": datetime.now()},
    ]
    _persist_managed_plants(db, plants)
    st.session_state.ecocare_managed_plants = plants


def _plant_image_source(plant):
    image_data = plant.get("image_data")
    if image_data:
        if isinstance(image_data, str):
            return image_data.encode("ascii")
        return image_data
    return plant.get("image_url", "")


def _mark_plant_watered(plant, db):
    plants = list(st.session_state.ecocare_managed_plants)
    plant_index = next(
        (
            index
            for index, managed_plant in enumerate(plants)
            if (
                managed_plant.get("custom_plant_id")
                and managed_plant.get("custom_plant_id") == plant.get("custom_plant_id")
            )
            or (
                not managed_plant.get("custom_plant_id")
                and not plant.get("custom_plant_id")
                and managed_plant["name"] == plant["name"]
            )
        ),
        None,
    )
    if plant_index is None:
        raise ValueError(f"{plant['name']} is not in your plant collection.")

    watered_at = datetime.now()
    updated_plants = list(plants)
    updated_plants[plant_index] = {**plants[plant_index], "last_watered_at": watered_at}
    event = {"name": plant["name"], "watered_at": watered_at.isoformat()}
    user_ref = db.collection("users").document(st.session_state["user_uid"])
    batch = db.batch()
    batch.set(
        user_ref.collection("watering_events").document(uuid.uuid4().hex),
        event,
    )
    batch.set(
        user_ref,
        {"managed_plants": _managed_plants_for_storage(updated_plants)},
        merge=True,
    )
    batch.commit()
    st.session_state.ecocare_managed_plants = updated_plants
    st.session_state.ecocare_watering_log.append(event)
    st.toast(f"{plant['name']} marked as watered today.", icon="💧")


def _render_catalog_cards(plants, columns=3, page_key="catalog", db=None):
    page_size = 24
    signature_key = f"ecocare_catalog_signature_{page_key}"
    count_key = f"ecocare_catalog_count_{page_key}"
    signature = tuple(plant["name"] for plant in plants)
    if st.session_state.get(signature_key) != signature:
        st.session_state[signature_key] = signature
        st.session_state[count_key] = page_size
    visible_count = min(st.session_state.get(count_key, page_size), len(plants))

    for offset in range(0, visible_count, columns):
        row = st.columns(columns, gap="small")
        for column, plant in zip(row, plants[offset : min(offset + columns, visible_count)]):
            with column:
                with st.container(border=True):
                    image_source = _plant_image_source(plant)
                    if image_source:
                        st.image(image_source, use_container_width=True)
                    else:
                        st.markdown(f"### 🌿 {_safe(plant['name'])}")
                    st.markdown(f"**{_safe(plant['name'])}**")
                    st.caption(
                        f"{_safe(plant['scientific_name'])} · {_safe(plant['type'])}"
                    )
                    st.caption(
                        f"{_safe(plant['light'])} · Water {_safe(plant['water_frequency'].lower())}"
                    )
                    if plant.get("image_credit") and plant.get("image_source_url"):
                        st.markdown(
                            f'Photo: [{_safe(plant["image_credit"])}]'
                            f'({_safe(plant["image_source_url"])}) · '
                            f'{_safe(plant.get("image_license", ""))}'
                        )
                    if db is not None:
                        _init_managed_plants(db)
                        managed = any(
                            (
                                item.get("custom_plant_id")
                                and item.get("custom_plant_id") == plant.get("custom_plant_id")
                            )
                            or (
                                not item.get("custom_plant_id")
                                and not plant.get("custom_plant_id")
                                and item["name"].casefold() == plant["name"].casefold()
                            )
                            for item in st.session_state.ecocare_managed_plants
                        )
                        if managed:
                            st.button(
                                "💧 Mark as Watered",
                                key=f"{page_key}_water_{plant.get('custom_plant_id', plant['name'])}",
                                use_container_width=True,
                                on_click=_mark_plant_watered,
                                args=(plant, db),
                            )
                        elif plant.get("name") in PLANTS_BY_NAME:
                            st.button(
                                "+ Add to My Plants",
                                key=f"{page_key}_add_{plant['name']}",
                                use_container_width=True,
                                on_click=_add_plant_to_collection,
                                args=(plant["name"], db),
                            )
    st.caption(f"Showing {visible_count} of {len(plants)} plants")
    if visible_count < len(plants) and st.button(
        "Load more plants",
        key=f"ecocare_catalog_load_more_{page_key}",
        use_container_width=True,
    ):
        st.session_state[count_key] = min(visible_count + page_size, len(plants))
        st.rerun()


def render_compact_plant_library():
    """Show the full searchable catalog in the Weather Monitoring view."""
    st.markdown("### 🌱 Urban Plant Library")
    db = st.session_state.get("ecocare_firestore")
    if db is not None:
        _init_managed_plants(db)
    catalog = [*PLANT_CATALOG, *_custom_plants_in_collection()]
    st.caption(f"Browse care basics for {len(catalog)} plants in your urban garden.")
    search_col, type_col = st.columns([2, 1])
    with search_col:
        query = st.text_input(
            "Search library",
            placeholder="Search by plant or scientific name...",
            key="weather_plant_library_search",
            label_visibility="collapsed",
        ).strip()
    with type_col:
        plant_type = st.selectbox(
            "Plant type",
            ["All Plants", "Indoor", "Outdoor"],
            key="weather_plant_library_type",
            label_visibility="collapsed",
        )
    query = query.casefold()
    filtered = [
        plant for plant in _plants_for_query(catalog, query)
        if plant_type == "All Plants" or plant["type"] == plant_type
    ]
    _render_catalog_cards(filtered, page_key="weather", db=db)


@st.dialog("Add a plant")
def _add_plant_dialog(db):
    _init_managed_plants(db)
    current_names = {
        plant["name"].casefold()
        for plant in st.session_state.ecocare_managed_plants
    }
    available = [
        plant for plant in PLANT_CATALOG
        if plant["name"].casefold() not in current_names
    ]
    if not available:
        st.info("All plants in the library are already in your collection.")
        return

    chosen_name = st.selectbox("Choose a plant", [plant["name"] for plant in available])
    chosen = PLANTS_BY_NAME[chosen_name]
    st.image(chosen["image_url"], width=160)
    st.caption(f"{chosen['scientific_name']} · {chosen['light']} · Water {chosen['water_frequency'].lower()}.")
    if chosen.get("image_credit") and chosen.get("image_source_url"):
        st.markdown(
            f'Photo: [{_safe(chosen["image_credit"])}]({_safe(chosen["image_source_url"])}) '
            f'· {_safe(chosen.get("image_license", ""))}'
        )
    st.button(
        "Add to My Plants",
        type="primary",
        use_container_width=True,
        key="ecocare_confirm_add",
        on_click=_add_plant_to_collection,
        args=(chosen_name, db),
    )


@st.dialog("Add your own plant")
def _add_custom_plant_dialog(db):
    name = st.text_input("Plant name", key="ecocare_custom_plant_name")
    scientific_name = st.text_input(
        "Scientific name (optional)",
        key="ecocare_custom_plant_scientific_name",
    )
    plant_type = st.selectbox(
        "Plant type",
        ["Indoor", "Outdoor"],
        key="ecocare_custom_plant_type",
    )
    light = st.text_input(
        "Light requirement",
        value="Bright, indirect light",
        key="ecocare_custom_plant_light",
    )
    water_frequency = st.text_input(
        "Watering frequency",
        value="When the topsoil feels dry",
        key="ecocare_custom_plant_water",
    )
    description = st.text_area(
        "Care notes",
        key="ecocare_custom_plant_description",
        max_chars=1000,
    )
    uploaded_photo = st.file_uploader(
        "Plant photo (optional)",
        type=["jpg", "jpeg", "png"],
        key="ecocare_custom_plant_photo",
    )
    if uploaded_photo:
        st.image(uploaded_photo, width=180)

    if st.button(
        "Save to My Plants",
        type="primary",
        use_container_width=True,
        key="ecocare_custom_plant_save",
    ):
        cleaned_name = name.strip()
        if not cleaned_name:
            st.error("Enter a plant name.")
            return
        if any(
            plant["name"].casefold() == cleaned_name.casefold()
            for plant in st.session_state.ecocare_managed_plants
        ):
            st.error("A plant with this name is already in your collection.")
            return

        image_data = None
        if uploaded_photo:
            try:
                image = Image.open(BytesIO(uploaded_photo.getvalue())).convert("RGB")
                image.thumbnail((512, 512))
                image_buffer = BytesIO()
                image.save(image_buffer, format="JPEG", quality=78, optimize=True)
                image_data = image_buffer.getvalue()
                if len(image_data) > 700_000:
                    st.error("This image is too large after compression. Please upload a smaller photo.")
                    return
            except (Image.DecompressionBombError, OSError, ValueError) as error:
                st.error(f"Could not process the plant photo: {error}")
                return

        custom_plant_id = uuid.uuid4().hex
        custom_plant = {
            "custom_plant_id": custom_plant_id,
            "name": cleaned_name,
            "scientific_name": scientific_name.strip() or "Not provided",
            "type": plant_type,
            "water_frequency": water_frequency.strip() or "When the topsoil feels dry",
            "light": light.strip() or "Bright, indirect light",
            "description": description.strip() or "A plant added to your personal collection.",
            "image_data": image_data,
            "last_watered_at": datetime.now(),
        }
        updated_plants = [
            *st.session_state.ecocare_managed_plants,
            custom_plant,
        ]
        user_ref = db.collection("users").document(st.session_state["user_uid"])
        batch = db.batch()
        batch.set(
            user_ref.collection("custom_plants").document(custom_plant_id),
            {key: value for key, value in custom_plant.items() if key != "last_watered_at"},
        )
        batch.set(
            user_ref,
            {"managed_plants": _managed_plants_for_storage(updated_plants)},
            merge=True,
        )
        try:
            batch.commit()
        except Exception as error:
            st.error(f"Could not save your plant: {error}")
            return

        st.session_state.ecocare_managed_plants = updated_plants
        st.toast(f"{cleaned_name} added to your plants.", icon="🌱")
        st.rerun()


def _render_weather_card(user_name, location, weather):
    today = date.today().strftime("%d %b %Y")
    if weather is None:
        st.error("Live weather is unavailable for this location. Check your weather API configuration and try again.")
        st.caption(f"📍 {location}")
        return
    details = weather.get("details", {})
    display_city = ", ".join(
        part for part in (weather.get("city"), weather.get("state")) if part
    )
    condition = _safe(weather.get("condition_text", ""))
    weather_icon = "⛈️" if "thunder" in condition.casefold() else (
        "🌧️" if "rain" in condition.casefold() else (
            "☀️" if "clear" in condition.casefold() or "sun" in condition.casefold() else "⛅"
        )
    )
    st.markdown(
        f"""
        <div class="eco-header">
            <div>
                <h1>Good Morning, {_safe(user_name)}! 🌿</h1>
                <p>Let's keep your plants healthy and growing.</p>
            </div>
            <div class="eco-date"><span>♧</span> Today, {today}</div>
        </div>
        <div class="eco-weather-card">
            <div class="eco-weather-head"><strong>Today's Weather</strong><span>📍 {_safe(display_city or location)}</span></div>
            <div class="eco-weather-main">
                <div><b>{weather["temp_c"]}°C</b><span>{condition}</span></div>
                <div class="eco-sun-cloud" aria-label="{condition}">{weather_icon}</div>
            </div>
            <div class="eco-weather-stats">
                <div><span>♧</span><small>Humidity<br><b>{_safe(details.get("humidity", "—"))}</b></small></div>
                <div><span>☂</span><small>Rain Chance<br><b>{_safe(details.get("precip", "—"))}</b></small></div>
                <div><span>≋</span><small>Wind Speed<br><b>{_safe(details.get("wind", "—"))}</b></small></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Live conditions · {_safe(weather.get('source', ''))} · Updated {datetime.now().strftime('%I:%M %p')}")


def _render_growth_card(db):
    _init_managed_plants(db)
    plants = st.session_state.ecocare_managed_plants
    now = datetime.now()
    on_schedule = sum(
        _plant_care_status(plant, now) in ("Excellent", "Good")
        for plant in plants
    )
    care_score = round(on_schedule / len(plants) * 100) if plants else 0
    week_start = now.date() - timedelta(days=6)
    activity = {week_start + timedelta(days=i): 0 for i in range(7)}
    plants_watered = set()
    for event in st.session_state.ecocare_watering_log:
        watered_at = datetime.fromisoformat(event["watered_at"])
        if watered_at.date() in activity:
            activity[watered_at.date()] += 1
            plants_watered.add(event["name"])
    max_activity = max(activity.values(), default=0)
    bars = "".join(
        f'<div class="eco-growth-day"><i style="height:{round(count / max(max_activity, 1) * 55)}px"></i>'
        f'<small>{day.strftime("%a")}</small></div>'
        for day, count in activity.items()
    )
    st.markdown(
        f"""
        <div class="eco-growth-card">
            <h3>↗ &nbsp; Weekly Plant Care Progress</h3>
            <div class="eco-growth-content">
                <div class="eco-donut" style="background:conic-gradient(#13864f 0 {care_score}%,#c8eddb {care_score}% 100%)"><div><b>{care_score}%</b><small>On-schedule care</small></div></div>
                <div class="eco-growth-chart">{bars}</div>
            </div>
            <p>Recorded watering this week <strong>{len(plants_watered)} plants · {sum(activity.values())} waterings</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_library_feature():
    featured = ["Snake Plant", "Peace Lily", "Money Plant", "Croton", "Jade Plant"]
    plants = [PLANTS_BY_NAME[name] for name in featured]
    thumbs = "".join(
        f'<div class="eco-feature-thumb">{_image(plant)}<span>{_safe(plant["name"])}</span></div>'
        for plant in plants
    )
    st.markdown(
        f"""
        <div class="eco-feature-card">
            <div class="eco-feature-head"><div><h3>Plant Library</h3><p>Explore {len(PLANT_CATALOG)} urban plants</p></div></div>
            <div class="eco-feature-thumbs">{thumbs}</div>
            <p class="eco-feature-description">Browse plant photos, care guides, and growing tips for indoor and outdoor plants.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("View All →", key="ecocare_view_all", type="secondary"):
        st.session_state.ecocare_show_all_plants = not st.session_state.get("ecocare_show_all_plants", False)
        st.rerun()


def _render_plant_card(plant, index, db):
    watered = _days_since_watered(plant)
    watered_text = "Today" if watered == 0 else f"{watered} day{'s' if watered != 1 else ''} ago"
    with st.container(border=True):
        image_source = _plant_image_source(plant)
        if image_source:
            st.image(image_source, use_container_width=True)
        else:
            st.markdown("### 🌿")
        st.markdown(f"**{_safe(plant['name'])}**")
        st.caption(
            f"{_safe(plant['scientific_name'])} · {_safe(plant['type'])} · "
            f"Last watered {watered_text}"
        )
    st.button(
        "💧 Mark as Watered",
        key=f"ecocare_water_{index}_{plant['name']}",
        use_container_width=True,
        on_click=_mark_plant_watered,
        args=(plant, db),
    )


def _render_my_plants(db):
    _init_managed_plants(db)
    user_name = st.session_state.get("user", {}).get("name", "Vasantha")
    st.markdown(
        f'<div class="eco-section-heading"><div><h2>🌿 &nbsp;My Plants</h2>'
        f'<p>Manage your plant care and keep them happy, {_safe(user_name)}!</p></div></div>',
        unsafe_allow_html=True,
    )
    search_col, filter_col, add_library_col, add_custom_col = st.columns(
        [2.2, 0.9, 1, 1.2],
        gap="small",
    )
    with search_col:
        query = st.text_input(
            "Search plants",
            placeholder="⌕  Search plants...",
            key="ecocare_my_plants_search",
            label_visibility="collapsed",
        ).strip()
    with filter_col:
        selected_type = st.selectbox(
            "Filter plants",
            ["All Plants", "Indoor", "Outdoor"],
            key="ecocare_my_plants_type",
            label_visibility="collapsed",
        )
    with add_library_col:
        if st.button(
            "+ Library",
            key="ecocare_add_plant",
            type="primary",
            use_container_width=True,
        ):
            _add_plant_dialog(db)
    with add_custom_col:
        if st.button(
            "+ Your Plant",
            key="ecocare_add_custom_plant",
            use_container_width=True,
        ):
            _add_custom_plant_dialog(db)

    query = _search_query("ecocare_my_plants_search")
    filtered = [
        (index, plant)
        for index, plant in enumerate(st.session_state.ecocare_managed_plants)
        if (not query or query in plant["name"].casefold() or query in plant["scientific_name"].casefold()
            or query in plant["description"].casefold())
        and (selected_type == "All Plants" or plant["type"] == selected_type)
    ]
    if not filtered:
        st.info("No plants match your search. Try a different name or add a plant from the library.")
        return
    for offset in range(0, len(filtered), 3):
        columns = st.columns(3, gap="small")
        for column, (index, plant) in zip(columns, filtered[offset : offset + 3]):
            with column:
                _render_plant_card(plant, index, db)


def _render_reports(db):
    _init_managed_plants(db)
    plants = st.session_state.ecocare_managed_plants
    now = datetime.now()
    week_start = now.date() - timedelta(days=6)
    statuses = {status: 0 for status in ("Excellent", "Good", "Fair", "Needs Attention")}
    for plant in plants:
        statuses[_plant_care_status(plant, now)] += 1

    events_by_day = {week_start + timedelta(days=i): 0 for i in range(7)}
    watered_this_week = set()
    for event in st.session_state.ecocare_watering_log:
        watered_at = datetime.fromisoformat(event["watered_at"])
        if week_start <= watered_at.date() <= now.date():
            events_by_day[watered_at.date()] += 1
            watered_this_week.add(event["name"])

    total = len(plants)
    doing_well = statuses["Excellent"] + statuses["Good"]
    health_percent = round(doing_well / total * 100) if total else 0
    colors = {
        "Excellent": "#45b99b",
        "Good": "#9ccc65",
        "Fair": "#ffca55",
        "Needs Attention": "#ef7181",
    }
    gradient_stops = []
    position = 0.0
    if total:
        for status, count in statuses.items():
            end = position + count / total * 100
            gradient_stops.append(f"{colors[status]} {position:.2f}% {end:.2f}%")
            position = end
    else:
        gradient_stops = ["#e8efeb 0% 100%"]
    summary_gradient = ", ".join(gradient_stops)

    max_events = max(events_by_day.values(), default=0)
    trend_bars = "".join(
        f'<div class="eco-trend-bar">'
        f'<span>{events_by_day[day]}</span>'
        f'<i style="height:{events_by_day[day] / max(max_events, 1) * 100:.1f}%"></i>'
        f'<small>{day.strftime("%a")}</small></div>'
        for day in events_by_day
    )
    report_data = {
        "week_start": week_start.isoformat(),
        "week_end": now.date().isoformat(),
        "generated_at": now.isoformat(),
        "plant_count": total,
        "status_counts": statuses,
        "on_schedule_count": doing_well,
        "care_progress_percent": health_percent,
        "watered_plant_count": len(watered_this_week),
        "watering_count": sum(events_by_day.values()),
        "growth_trend": [
            {"date": day.isoformat(), "watering_count": count}
            for day, count in events_by_day.items()
        ],
    }
    report_signature = json.dumps(
        {key: value for key, value in report_data.items() if key != "generated_at"},
        sort_keys=True,
    )
    report_cache_key = f"ecocare_weekly_report_{st.session_state['user_uid']}_{week_start.isoformat()}"
    if st.session_state.get(report_cache_key) != report_signature:
        db.collection("users").document(st.session_state["user_uid"]).collection(
            "weekly_reports"
        ).document(week_start.isoformat()).set(report_data, merge=True)
        st.session_state[report_cache_key] = report_signature
    st.markdown(
        f"""
        <div class="eco-section-heading eco-report-heading">
          <div><h2>▥ &nbsp;Weekly Reports</h2>
          <p>Care activity and watering status from your plant collection</p></div>
          <span class="eco-report-date">▦ &nbsp;{week_start.strftime("%d %b %Y")} – {now.strftime("%d %b %Y")}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_growth, col_trend, col_stats = st.columns([1, 1, 1.08], gap="small")
    with col_growth:
        st.markdown(
            f"""
            <div class="eco-report-card">
              <h3>🌿 &nbsp;Plant Growth Summary</h3>
              <div class="eco-summary">
                <div class="eco-donut report-donut" style="background:conic-gradient({summary_gradient})">
                  <div><b>{health_percent}%</b><small>On-schedule care</small></div>
                </div>
                <ul>
                  {''.join(f'<li><i style="background:{colors[status]}"></i>{status}<b>{count}</b></li>' for status, count in statuses.items())}
                </ul>
              </div>
              <p class="eco-report-note">Based on watering schedules for {total} plants in your collection.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_trend:
        st.markdown(
            f"""
            <div class="eco-report-card">
              <h3>↗ &nbsp;Weekly Growth Trend</h3>
              <p class="eco-report-note">Your recorded watering activity · plants watered per day</p>
              <div class="eco-trend">
                <div class="eco-y-labels"><span>{max_events}</span><span>{round(max_events * .75)}</span><span>{round(max_events * .5)}</span><span>{round(max_events * .25)}</span><span>0</span></div>
                <div class="eco-trend-bars">{trend_bars}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_stats:
        st.markdown(
            f"""
            <div class="eco-report-card">
              <h3>♧ &nbsp;Plant Care Reports</h3>
              <p class="eco-report-note">Live summary of your saved plant care activity</p>
              <div class="eco-care-stats">
                <div><span class="care-icon blue">♧</span><small>Watered this week</small><b>{len(watered_this_week)} plants</b></div>
                <div><span class="care-icon green">◉</span><small>On schedule</small><b>{doing_well} plants</b></div>
                <div><span class="care-icon amber">⚠</span><small>Needs attention</small><b>{statuses["Needs Attention"]} plants</b></div>
                <div><span class="care-icon green">♧</span><small>Total Plants</small><b>{total} plants</b></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _shift_calendar_month(month_start, offset):
    month_index = month_start.year * 12 + month_start.month - 1 + offset
    year, month_index = divmod(month_index, 12)
    return date(year, month_index + 1, 1)


def _render_calendar(db):
    user_id = st.session_state.get("user_uid")
    if not user_id:
        raise RuntimeError("Cannot load calendar data without an authenticated user.")

    today = date.today()
    month_key = f"ecocare_calendar_month_{user_id}"
    selected_key = f"ecocare_calendar_selected_{user_id}"
    st.session_state.setdefault(month_key, today.replace(day=1))
    st.session_state.setdefault(selected_key, today.isoformat())

    month_start = st.session_state[month_key]
    if isinstance(month_start, str):
        month_start = date.fromisoformat(month_start)
    selected_date = date.fromisoformat(st.session_state[selected_key])
    month_end = date(
        month_start.year,
        month_start.month,
        calendar_module.monthrange(month_start.year, month_start.month)[1],
    )
    next_month = _shift_calendar_month(month_start, 1)
    entries_ref = db.collection("users").document(user_id).collection("calendar_entries")
    watering_events_ref = db.collection("users").document(user_id).collection("watering_events")
    try:
        saved_entries = (
            entries_ref.where("date", ">=", month_start.isoformat())
            .where("date", "<=", month_end.isoformat())
            .stream()
        )
        notes_by_date = {}
        for entry in saved_entries:
            entry_data = entry.to_dict() or {}
            entry_date = entry_data.get("date", entry.id)
            note = entry_data.get("note", "")
            if note.strip():
                notes_by_date[entry_date] = note
        month_watering_events = watering_events_ref.where(
            "watered_at", ">=", month_start.isoformat()
        ).where("watered_at", "<", next_month.isoformat()).stream()
        watering_dates = {
            datetime.fromisoformat((event.to_dict() or {})["watered_at"])
            .date()
            .isoformat()
            for event in month_watering_events
        }
    except Exception as error:
        st.error(f"Could not load calendar entries: {error}")
        return

    previous_col, month_col, next_col = st.columns([1, 3, 1])
    with previous_col:
        previous_month = st.button(
            "‹",
            key=f"ecocare_calendar_previous_{user_id}",
            help="Previous month",
            use_container_width=True,
        )
    with month_col:
        st.markdown(
            f"<h3 style='text-align:center;margin:0 0 10px'>"
            f"{month_start.strftime('%B %Y')}</h3>",
            unsafe_allow_html=True,
        )
    with next_col:
        next_month = st.button(
            "›",
            key=f"ecocare_calendar_next_{user_id}",
            help="Next month",
            use_container_width=True,
        )

    if previous_month or next_month:
        offset = -1 if previous_month else 1
        month_start = _shift_calendar_month(month_start, offset)
        st.session_state[month_key] = month_start
        selected_date = date(
            month_start.year,
            month_start.month,
            min(
                selected_date.day,
                calendar_module.monthrange(month_start.year, month_start.month)[1],
            ),
        )
        st.session_state[selected_key] = selected_date.isoformat()
        st.rerun()

    weekdays = st.columns(7, gap="small")
    for column, weekday in zip(weekdays, ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")):
        with column:
            st.caption(weekday)

    for week in calendar_module.Calendar(firstweekday=6).monthdayscalendar(
        month_start.year, month_start.month
    ):
        day_columns = st.columns(7, gap="small")
        for column, day in zip(day_columns, week):
            with column:
                if not day:
                    st.markdown("&nbsp;")
                    continue
                calendar_date = date(month_start.year, month_start.month, day)
                iso_date = calendar_date.isoformat()
                markers = (" •" if iso_date in notes_by_date else "")
                if iso_date in watering_dates:
                    markers += " 💧"
                if calendar_date == today:
                    markers += " ·"
                if st.button(
                    f"{day}{markers}",
                    key=f"ecocare_calendar_day_{user_id}_{iso_date}",
                    type="primary" if calendar_date == selected_date else "secondary",
                    use_container_width=True,
                ):
                    st.session_state[selected_key] = iso_date

    st.caption("• Note   💧 Watering activity   · Today")
    selected_date = date.fromisoformat(st.session_state[selected_key])
    st.markdown(f"**{selected_date.strftime('%A, %B %d, %Y')}**")
    note_key = f"ecocare_calendar_note_{user_id}_{selected_date.isoformat()}"
    st.session_state.setdefault(note_key, notes_by_date.get(selected_date.isoformat(), ""))
    st.text_area(
        "Daily note",
        key=note_key,
        placeholder="Add a note or reminder for this date...",
        max_chars=2000,
        label_visibility="collapsed",
    )
    if st.button(
        "Save note",
        key=f"ecocare_calendar_save_{user_id}_{selected_date.isoformat()}",
        type="primary",
        use_container_width=True,
    ):
        note = st.session_state[note_key].strip()
        note_ref = entries_ref.document(selected_date.isoformat())
        try:
            if note:
                note_ref.set({
                    "date": selected_date.isoformat(),
                    "note": note,
                    "updated_at": datetime.now().isoformat(),
                })
            elif selected_date.isoformat() in notes_by_date:
                note_ref.delete()
        except Exception as error:
            st.error(f"Could not save your calendar note: {error}")
        else:
            st.toast("Calendar note saved.", icon="✅")
            st.rerun()


def render_dashboard(db=None):
    """Render the responsive EcoCare home dashboard."""
    db = db or st.session_state.get("ecocare_firestore")
    if db is None:
        raise RuntimeError("Firestore is not configured for the dashboard.")
    _init_managed_plants(db)
    user = st.session_state.get("user", {})
    user_name = user.get("name", "Vasantha")
    location = user.get("location", "Chennai, Tamil Nadu")
    city, state = _profile_place()
    try:
        weather = _get_live_weather(city, state)
    except (RuntimeError, ValueError) as error:
        st.warning(f"Could not load live weather: {_safe(error)}")
        weather = None
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {background:#f8fbf9;color:#172b35}
        .stApp, [class*="css"] {font-family:Inter, sans-serif}
        [data-testid="stMainBlockContainer"] {max-width:1500px;padding-top:1.75rem!important;padding-bottom:1rem}
        .eco-header {display:flex;justify-content:space-between;align-items:center;margin:0 0 18px}
        .eco-header h1 {font-size:26px;margin:0 0 4px;color:#182b35;font-weight:700}
        .eco-header p,.eco-section-heading p {font-size:13px;color:#667680;margin:0}
        .eco-date {font-size:12px;color:#31474d;display:flex;gap:10px;align-items:center}
        .eco-weather-card,.eco-growth-card,.eco-feature-card,.eco-plant-card,.eco-report-card {border:1px solid #e3ebe7;border-radius:15px;background:#fff;box-shadow:0 3px 12px rgba(22,55,39,.035)}
        .eco-weather-card {height:184px;padding:14px 16px;background:linear-gradient(125deg,#eaf7ff,#c9e6fa)}
        .eco-weather-head {display:flex;flex-direction:column;gap:5px;font-size:14px}
        .eco-weather-head span {font-size:11px;color:#475e68}
        .eco-weather-main {display:flex;align-items:center;justify-content:space-between;margin:9px 10px 10px 0}
        .eco-weather-main b {display:block;font-size:31px;line-height:1.1}
        .eco-weather-main span {font-size:12px}
        .eco-sun-cloud {font-size:36px;position:relative}
        .eco-sun-cloud span {position:absolute;right:-15px;bottom:-1px;font-size:29px}
        .eco-weather-stats {display:flex;border-top:1px solid rgba(39,83,102,.12);padding-top:8px;justify-content:space-between}
        .eco-weather-stats div {display:flex;gap:5px;align-items:center;font-size:15px}
        .eco-weather-stats small {font-size:9px;color:#425963}
        .eco-weather-stats b {font-size:10px;color:#172b35}
        .eco-growth-card {height:184px;background:#f1f8e9;padding:14px 16px}
        .eco-growth-card h3,.eco-feature-card h3,.eco-report-card h3 {font-size:13px;margin:0;color:#1b2c34}
        .eco-growth-content {height:110px;display:flex;align-items:center;justify-content:space-around}
        .eco-donut {width:92px;height:92px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#13864f 0 0%,#c8eddb 0 100%);position:relative;flex:none}
        .eco-donut:before {content:"";position:absolute;inset:9px;border-radius:50%;background:#f1f8e9}
        .eco-donut div {position:relative;text-align:center;display:flex;flex-direction:column}
        .eco-donut b {font-size:17px}.eco-donut small {font-size:8px}
        .eco-growth-chart {height:75px;display:flex;align-items:flex-end;gap:8px;padding:8px;background:rgba(255,255,255,.5);border:1px solid rgba(24,113,74,.08);border-radius:10px}
        .eco-growth-day {height:100%;display:flex;align-items:center;justify-content:flex-end;flex-direction:column;gap:2px}
        .eco-growth-day i {display:block;width:10px;background:linear-gradient(#80c89d,#15934e);border-radius:4px 4px 0 0}
        .eco-growth-day small {font-size:6px;color:#667680}
        .eco-growth-card>p {font-size:9px;color:#627064;margin:0}.eco-growth-card>p strong {display:block;color:#22834c;font-size:12px;margin-top:3px}
        .eco-feature-card {height:154px;padding:13px 14px 8px}
        .eco-feature-card p {font-size:10px;color:#65727a;margin:4px 0}
        .eco-feature-thumbs {display:flex;gap:5px;margin:10px 0 7px}
        .eco-feature-thumb {width:20%;min-width:0}
        .eco-feature-thumb img {width:100%;height:48px;object-fit:cover;border-radius:6px;display:block}
        .eco-feature-thumb span {display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:8px;color:#4b5c5f;margin-top:3px}
        .eco-feature-card .eco-feature-description {font-size:9px;line-height:1.35}
        .eco-section-heading {display:flex;justify-content:space-between;align-items:center;margin:20px 0 10px}
        .eco-section-heading h2 {font-size:19px;margin:0 0 3px;color:#172b35}
        .eco-report-heading {margin-top:22px}
        .eco-report-date {font-size:10px;color:#475a60;border:1px solid #e5ece9;padding:7px 9px;border-radius:8px}
        .eco-plant-card {padding:8px 8px 6px}
        .eco-plant-photo {height:112px;position:relative;border-radius:8px;overflow:hidden;background:#eef4ef}
        .eco-plant-photo img {width:100%;height:100%;object-fit:cover;display:block}
        .eco-plant-menu {position:absolute;right:7px;top:5px;border-radius:5px;background:#ffffffdf;padding:0px 6px;font-weight:700}
        .eco-plant-badge {position:absolute;right:6px;bottom:6px;border-radius:5px;background:#81c784;color:#fff;padding:2px 7px;font-size:9px}
        .eco-plant-badge.outdoor {background:#42a5f5}
        .eco-plant-card h3 {font-size:12px;margin:8px 0 2px;color:#182b35}
        .eco-plant-card em {font-size:10px;color:#718087;display:block}
        .eco-watered {margin-top:8px;font-size:10px;color:#4d636e;padding-bottom:2px}
        [data-testid="stMain"] .stButton>button {min-height:30px;padding:4px 8px;border-radius:8px;background:#e8f5ed;color:#226c47;border:1px solid #d9eee1;font-size:10px;font-weight:600}
        [data-testid="stMain"] .stButton>button:hover {background:#d7efdf;border-color:#b9dfc7;color:#155b37;transform:translateY(-1px)}
        .eco-report-card {height:auto;min-height:190px;padding:12px;box-sizing:border-box;overflow:hidden}
        .eco-report-card h3 {font-size:11px}
        .eco-summary {display:flex;align-items:center;justify-content:space-around;margin-top:12px}
        .report-donut {width:76px;height:76px;background:conic-gradient(#13864f 0 0%,#c8eddb 0 100%)}
        .report-donut:before {inset:8px;background:white}.report-donut b {font-size:14px}
        .eco-summary ul {list-style:none;padding:0;margin:0;width:51%;font-size:9px}
        .eco-summary li {display:flex;align-items:center;gap:6px;margin:7px 0}
        .eco-summary li b {margin-left:auto}
        .eco-summary li i {width:7px;height:7px;border-radius:50%;background:#48b99a}
        .eco-summary li i.lime {background:#9ccc65}.eco-summary li i.yellow {background:#ffca55}.eco-summary li i.red {background:#ef7181}
        .eco-trend {height:112px;display:flex;margin-top:9px;min-width:0}
        .eco-y-labels {display:flex;flex-direction:column;justify-content:space-between;color:#79858b;font-size:7px;padding:0 5px 15px 0}
        .eco-trend-bars {border-bottom:1px solid #dfe7e3;flex:1;min-width:0;display:flex;justify-content:space-around;align-items:flex-end;background:repeating-linear-gradient(to bottom,transparent 0,transparent 21px,#edf1ef 22px)}
        .eco-trend-bar {height:100%;display:flex;align-items:center;justify-content:flex-end;flex-direction:column;gap:3px;width:11%;min-width:0}
        .eco-trend-bar span {font-size:8px;color:#50615b;line-height:10px}
        .eco-trend-bar i {width:65%;background:linear-gradient(#5ab475,#21834b);border-radius:3px 3px 0 0}
        .eco-trend-bar small {font-size:7px;color:#596a70;line-height:10px}
        .eco-report-note {font-size:9px;color:#74827b;margin:6px 0 0;line-height:1.35}
        [data-testid="stTextInput"] input {background:#fff!important;color:#172b35!important;border:1px solid #dce7e1!important;border-radius:9px!important;min-height:40px!important}
        [data-testid="stSelectbox"] div[data-baseweb="select"]>div {background:#fff;color:#172b35;border-color:#dce7e1;border-radius:9px}
        [data-testid="stMain"] [data-testid="stHorizontalBlock"] {align-items:stretch}
        .eco-care-stats {display:flex;justify-content:space-between;margin-top:16px}
        .eco-care-stats>div {display:flex;flex-direction:column;align-items:center;gap:4px;flex:1;border-right:1px solid #edf0ef}
        .eco-care-stats>div:last-child {border:0}
        .eco-care-stats small {font-size:7px;color:#69777b;text-align:center}
        .eco-care-stats b {font-size:9px;white-space:nowrap}
        .care-icon {width:29px;height:29px;border-radius:50%;background:#eef8fb;display:grid;place-items:center;font-size:14px}
        .care-icon.blue {color:#33a2d3}.care-icon.green {color:#41945c;background:#f0f8f0}.care-icon.amber {color:#e2a33e;background:#fff8ea}
        .eco-library-card {background:#fff;border:1px solid #e5ece8;border-radius:12px;overflow:hidden;margin-bottom:12px;transition:transform .18s,box-shadow .18s}
        .eco-library-card:hover {transform:translateY(-3px);box-shadow:0 8px 20px #173b2414}
        .eco-library-image {display:block;width:100%;height:145px;object-fit:cover;background:#eef4ef}
        .eco-library-card-copy {padding:11px;display:flex;flex-direction:column;gap:4px}
        .eco-library-card-copy strong {font-size:13px}.eco-library-card-copy em {font-size:10px;color:#718087}
        .eco-library-card-copy span {font-size:10px;color:#55715f}
        .eco-image-credit {font-size:9px;line-height:1.35;color:#718087}
        .eco-image-credit a {color:#55715f;text-decoration:none}
        .eco-image-credit a:hover {text-decoration:underline}
        .eco-calendar-title {font-size:18px;margin:0 0 8px;color:#172b35}
        div[class*="st-key-ecocare_calendar_day_"] button {min-height:54px;font-size:14px}
        div[class*="st-key-ecocare_calendar_previous_"] button,
        div[class*="st-key-ecocare_calendar_next_"] button {min-height:42px;font-size:22px}
        @media(max-width:900px){.eco-weather-card,.eco-growth-card{height:auto;min-height:176px}.eco-feature-card{height:auto;min-height:154px}.eco-report-card{height:auto;min-height:190px}.eco-plant-photo{height:140px}}
        @media(max-width:600px){.eco-header{align-items:flex-start;gap:12px;flex-direction:column}.eco-header h1{font-size:22px}.eco-date{align-self:flex-end}.eco-plant-photo{height:105px}.eco-report-date{font-size:8px}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    first, second, third = st.columns([1.08, 1, 1], gap="small")
    with first:
        _render_weather_card(user_name, location, weather)
    with second:
        _render_growth_card(db)
    with third:
        _render_library_feature()

    st.markdown('<h2 class="eco-calendar-title">📅 &nbsp;Calendar</h2>', unsafe_allow_html=True)
    _render_calendar(db)

    if st.session_state.get("ecocare_show_all_plants", False):
        st.markdown("### 🌱 Explore the Urban Plant Library")
        all_library_plants = [*PLANT_CATALOG, *_custom_plants_in_collection()]
        st.caption(f"{len(all_library_plants)} plants · care tips for indoor and outdoor spaces")
        search_col, filter_col = st.columns([2, 1])
        with search_col:
            library_query = st.text_input(
                "Search all plants",
                placeholder=f"Search all {len(all_library_plants)} plants...",
                key="ecocare_all_library_search",
                label_visibility="collapsed",
            ).strip()
        with filter_col:
            library_type = st.selectbox(
                "Library type",
                ["All Plants", "Indoor", "Outdoor"],
                key="ecocare_all_library_type",
                label_visibility="collapsed",
            )
        library_query = library_query.casefold()
        library_plants = [
            plant for plant in _plants_for_query(all_library_plants, library_query)
            if library_type == "All Plants" or plant["type"] == library_type
        ]
        _render_catalog_cards(library_plants, page_key="dashboard", db=db)

    _render_my_plants(db)
    _render_reports(db)
