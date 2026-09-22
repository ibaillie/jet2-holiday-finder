from datetime import date, timedelta
import secrets
import time

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Jet2 Holiday Finder", page_icon="🏖️", layout="wide")

SUPABASE_URL = "https://euksjqsvkmufskpnmdxj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV1a3NqcXN2a211ZnNrcG5tZHhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAwODIxNzIsImV4cCI6MjEwNTY1ODE3Mn0.Yu0xMxZwdBO3mvv_TN1DZPu3emz5or60234fmBosvAI"
FUNCTION_URL = f"{SUPABASE_URL}/functions/v1/run-jet2-search"

AIRPORTS = {"Glasgow": 69}
DESTINATIONS = {"Lanzarote": 154}
BOARD_IDS = {"All Inclusive": 5}
DEFAULT_HOTEL = "Iberostar Selection Lanzarote Park"


def get_client_token() -> str:
    token = st.query_params.get("u")
    if not token:
        token = secrets.token_urlsafe(24)
        st.query_params["u"] = token
    return str(token)


CLIENT_TOKEN = get_client_token()


def api_headers(prefer=None):
    h = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "x-client-token": CLIENT_TOKEN,
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def supabase_get(table, params):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=api_headers(),
        params=params,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def queue_search(payload):
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/search_jobs",
        headers=api_headers("return=representation"),
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    job = r.json()[0]

    trigger = requests.post(
        FUNCTION_URL,
        headers=api_headers(),
        json={"job_id": job["id"]},
        timeout=20,
    )
    trigger.raise_for_status()
    return job


def load_jobs(limit=20):
    return supabase_get(
        "search_jobs",
        {
            "select": "*",
            "order": "created_at.desc",
            "limit": str(limit),
        },
    )


def load_results(job_id):
    return supabase_get(
        "search_results",
        {
            "select": "*",
            "job_id": f"eq.{job_id}",
            "order": "total_price.asc,departure.asc",
        },
    )


st.title("🏖️ Jet2 Holiday Finder")
st.caption(
    "Start a search, close your phone, and come back later. "
    "Searches now run in the background and save their progress/results."
)

with st.sidebar:
    st.header("New search")

    airport_mode = st.selectbox("Departing airport", ["Glasgow", "Custom Jet2 airport ID"])
    airport_id = (
        AIRPORTS["Glasgow"]
        if airport_mode == "Glasgow"
        else st.number_input("Jet2 airport ID", min_value=1, value=69, step=1)
    )

    destination_mode = st.selectbox(
        "Destination", ["Lanzarote", "Custom Jet2 destination area ID"]
    )
    destination_id = (
        DESTINATIONS["Lanzarote"]
        if destination_mode == "Lanzarote"
        else st.number_input("Jet2 destination area ID", min_value=1, value=154, step=1)
    )

    hotel_name = st.text_input("Hotel name", value=DEFAULT_HOTEL)

    today = date.today()
    start_date = st.date_input("Earliest departure", value=today)
    end_date = st.date_input("Latest departure", value=today + timedelta(days=14))

    durations = st.multiselect(
        "Holiday length (nights)",
        options=[3, 4, 5, 7, 10, 11, 14],
        default=[7],
    )

    st.subheader("Travellers")
    adults = st.number_input("Adults", min_value=1, max_value=10, value=2, step=1)
    child_count = st.number_input(
        "Children aged 2+", min_value=0, max_value=6, value=1, step=1
    )

    child_ages = []
    for i in range(int(child_count)):
        child_ages.append(
            st.number_input(
                f"Child {i + 1} age at departure",
                min_value=2,
                max_value=17,
                value=4,
                step=1,
                key=f"child_age_{i}",
            )
        )

    infants = st.number_input("Infants under 2", min_value=0, max_value=4, value=1, step=1)
    board = st.selectbox("Board", ["All Inclusive"])
    max_price = st.number_input(
        "Maximum total price (£) — 0 means no limit",
        min_value=0,
        value=0,
        step=100,
    )

    start_button = st.button("🚀 Start background search", type="primary", use_container_width=True)

if start_button:
    if end_date < start_date:
        st.error("The latest departure must be on or after the earliest departure.")
    elif not durations:
        st.error("Choose at least one holiday length.")
    elif not hotel_name.strip():
        st.error("Enter a hotel name.")
    else:
        total_checks = ((end_date - start_date).days + 1) * len(durations)
        payload = {
            "owner_token": CLIENT_TOKEN,
            "hotel_name": hotel_name.strip(),
            "airport_id": int(airport_id),
            "destination_id": int(destination_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "durations": [int(x) for x in durations],
            "adults": int(adults),
            "child_ages": [int(x) for x in child_ages],
            "infants": int(infants),
            "board_id": BOARD_IDS[board],
            "max_price": float(max_price) if max_price else None,
            "total_checks": total_checks,
        }
        try:
            job = queue_search(payload)
            st.success(
                f"Search queued — {total_checks} date/duration checks. "
                "You can close this page now; it will keep running."
            )
            st.query_params["job"] = job["id"]
            time.sleep(1)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not queue the search: {exc}")

st.divider()

top1, top2 = st.columns([3, 1])
with top1:
    st.subheader("Saved searches")
with top2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

try:
    jobs = load_jobs()
except Exception as exc:
    st.error(f"Could not load saved searches: {exc}")
    jobs = []

if not jobs:
    st.info("No saved searches yet. Start one from the sidebar.")
    st.stop()

job_options = {}
for j in jobs:
    created = pd.to_datetime(j["created_at"]).strftime("%d %b %H:%M")
    label = (
        f"{created} · {j['hotel_name']} · "
        f"{j['start_date']} → {j['end_date']} · {j['status'].upper()}"
    )
    job_options[label] = j

wanted_id = st.query_params.get("job")
default_index = 0
if wanted_id:
    for i, (_, j) in enumerate(job_options.items()):
        if j["id"] == wanted_id:
            default_index = i
            break

selected_label = st.selectbox(
    "Open saved search",
    list(job_options.keys()),
    index=default_index,
)
job = job_options[selected_label]
st.query_params["job"] = job["id"]

status = job["status"]
completed = int(job.get("completed_checks") or 0)
total = int(job.get("total_checks") or 0)
matches = int(job.get("matches_found") or 0)
progress_value = completed / total if total else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Status", status.title())
c2.metric("Progress", f"{completed}/{total}")
c3.metric("Matches", matches)
c4.metric(
    "Cheapest so far",
    f"£{float(job['cheapest_price']):,.0f}" if job.get("cheapest_price") is not None else "—",
)

st.progress(min(max(progress_value, 0.0), 1.0))

if status in ("queued", "running"):
    st.info(
        "This search is running in the background. You can leave the app and come back later. "
        "Tap Refresh to check progress."
    )

try:
    results = load_results(job["id"])
except Exception as exc:
    st.error(f"Could not load results: {exc}")
    results = []

if results:
    df = pd.DataFrame(results)
    df["departure"] = pd.to_datetime(df["departure"]).dt.strftime("%d/%m/%Y")
    cheapest = float(df["total_price"].min())
    df["vs_cheapest"] = df["total_price"].astype(float) - cheapest

    display_cols = [
        "departure",
        "nights",
        "hotel",
        "resort",
        "destination",
        "hotel_stars",
        "tripadvisor",
        "room",
        "remaining",
        "total_price",
        "vs_cheapest",
        "promo_code",
        "jet2_link",
    ]
    df = df[[c for c in display_cols if c in df.columns]]

    st.subheader("Results — cheapest first")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "departure": "Departure",
            "nights": "Nights",
            "hotel": "Hotel",
            "resort": "Resort",
            "destination": "Destination",
            "hotel_stars": "Stars",
            "tripadvisor": "TripAdvisor",
            "room": "Room",
            "remaining": "Remaining",
            "total_price": st.column_config.NumberColumn("Total", format="£%.0f"),
            "vs_cheapest": st.column_config.NumberColumn("Vs cheapest", format="£%.0f"),
            "promo_code": "Promo",
            "jet2_link": st.column_config.LinkColumn("Jet2"),
        },
    )

    st.download_button(
        "⬇️ Download these results as CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="jet2_holiday_results.csv",
        mime="text/csv",
    )
elif status == "completed":
    st.warning("The search completed but no matching prices were found.")

if job.get("error_message"):
    with st.expander("Technical notes"):
        st.code(job["error_message"])

with st.expander("About saved searches"):
    st.markdown(
        """
        Your search history is now stored in a database rather than only in the browser session.

        The private identifier for this app session is kept in the page URL. If you bookmark or
        add this exact page to your Home Screen, the app can reopen the same saved history later.
        """
    )
