import time
from datetime import date, timedelta
from urllib.parse import urljoin

import pandas as pd
import streamlit as st
from curl_cffi import requests

st.set_page_config(page_title="Jet2 Holiday Finder", page_icon="🏖️", layout="wide")

JET2_ENDPOINT = "https://www.jet2holidays.com/api/jet2/search/search"
JET2_BASE = "https://www.jet2holidays.com"

# IDs we have directly verified from Jet2 searches.
AIRPORTS = {
    "Glasgow": 69,
}

DESTINATIONS = {
    "Lanzarote": 154,
}

BOARD_IDS = {
    "All Inclusive": 5,
}

DEFAULT_HOTEL = "Iberostar Selection Lanzarote Park"


def build_occupancy(adults: int, child_ages: list[int], infants: int) -> str:
    """Convert simple traveller inputs to Jet2's occupancy format."""
    code = str(adults)
    for age in child_ages:
        code += f"_{age}"
    if infants:
        code += f"-{infants}"
    return code


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def request_page(
    airport_id: int,
    destination_id: int,
    departure: date,
    duration: int,
    occupancy: str,
    page_number: int,
    page_size: int = 100,
):
    params = {
        "departureAirportIds": str(airport_id),
        "destinationAreaIds": str(destination_id),
        "departureDate": departure.isoformat(),
        "durations": str(duration),
        "occupancies": occupancy,
        "pageNumber": str(page_number),
        "pageSize": str(page_size),
        "sortOrder": "5",
        "filters": "",
        "holidayTypeId": "1",
        "flexibility": "0",
        "minPrice": "",
        "includePriceBreakDown": "false",
        "brandId": "",
        "inboundFlightId": "0",
        "outboundFlightId": "0",
        "gtmSearchType": "Beach Search Results",
        "searchId": "",
        "applyDiscount": "false",
        "occupancyOpen": "false",
        "useMultiSearch": "false",
        "defaultSearchParametersUsed": "false",
        "inboundFlightTimes": "",
        "outboundFlightTimes": "",
        "flexi": "",
    }

    response = requests.get(
        JET2_ENDPOINT,
        params=params,
        impersonate="chrome",
        http_version="v1",
        timeout=30,
        headers={
            "Referer": "https://www.jet2holidays.com/",
            "Accept": "application/json, text/plain, */*",
        },
    )
    response.raise_for_status()
    return response.json()


def find_hotel_for_date(
    hotel_query: str,
    airport_id: int,
    destination_id: int,
    departure: date,
    duration: int,
    occupancy: str,
    board_id: int,
):
    """
    Search enough result pages to find a hotel by exact/partial name.
    Returns the cheapest matching All Inclusive option for this date/duration.
    """
    page_size = 100
    first = request_page(
        airport_id,
        destination_id,
        departure,
        duration,
        occupancy,
        page_number=1,
        page_size=page_size,
    )

    total_results = int(first.get("totalResults", 0) or 0)
    max_pages = max(1, min(10, (total_results + page_size - 1) // page_size))

    pages = [first]
    for page_number in range(2, max_pages + 1):
        pages.append(
            request_page(
                airport_id,
                destination_id,
                departure,
                duration,
                occupancy,
                page_number=page_number,
                page_size=page_size,
            )
        )

    query = hotel_query.casefold().strip()
    matches = []

    for data in pages:
        for item in data.get("results", []):
            prop = item.get("property", {}) or {}
            name = str(prop.get("name", ""))
            if query not in name.casefold():
                continue

            board_prices = []
            for option in item.get("accommodationOptions", []) or []:
                if option.get("boardId") != board_id:
                    continue
                for price_option in option.get("priceOptions", []) or []:
                    price = price_option.get("totalPrice")
                    if price is not None:
                        board_prices.append((float(price), price_option))

            if not board_prices:
                continue

            total_price, price_option = min(board_prices, key=lambda x: x[0])

            rooms = item.get("rooms", []) or []
            room = rooms[0] if rooms else {}

            matches.append(
                {
                    "Departure": departure,
                    "Nights": duration,
                    "Hotel": name,
                    "Resort": prop.get("resort"),
                    "Destination": prop.get("area"),
                    "Hotel stars": prop.get("rating"),
                    "TripAdvisor": prop.get("tripAdvisorRating"),
                    "TripAdvisor reviews": prop.get("tripAdvisorReviewCount"),
                    "Room": room.get("description"),
                    "Remaining": room.get("remaining"),
                    "Total price": total_price,
                    "Price per paying person": price_option.get("pricePerPerson"),
                    "Discount": price_option.get("totalDiscount"),
                    "Promo code": price_option.get("promoCode"),
                    "Deposit": item.get("deposit"),
                    "Jet2 link": urljoin(JET2_BASE, item.get("url", "")),
                }
            )

    if not matches:
        return None

    return min(matches, key=lambda row: row["Total price"])


st.title("🏖️ Jet2 Holiday Finder")
st.caption(
    "Scan every departure day in a date range for one Jet2 hotel. "
    "This is an unofficial personal tool and uses Jet2's live website data."
)

with st.sidebar:
    st.header("Search")

    airport_mode = st.selectbox(
        "Departing airport",
        ["Glasgow", "Custom Jet2 airport ID"],
    )
    if airport_mode == "Custom Jet2 airport ID":
        airport_id = st.number_input("Jet2 airport ID", min_value=1, value=69, step=1)
    else:
        airport_id = AIRPORTS[airport_mode]

    destination_mode = st.selectbox(
        "Destination",
        ["Lanzarote", "Custom Jet2 destination area ID"],
    )
    if destination_mode == "Custom Jet2 destination area ID":
        destination_id = st.number_input(
            "Jet2 destination area ID", min_value=1, value=154, step=1
        )
    else:
        destination_id = DESTINATIONS[destination_mode]

    hotel_name = st.text_input("Hotel name", value=DEFAULT_HOTEL)

    today = date.today()
    default_end = today + timedelta(days=60)
    start_date = st.date_input("Earliest departure", value=today)
    end_date = st.date_input("Latest departure", value=default_end)

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

    infants = st.number_input(
        "Infants under 2", min_value=0, max_value=4, value=1, step=1
    )

    board = st.selectbox("Board", ["All Inclusive"])
    max_price = st.number_input(
        "Maximum total price (£) — 0 means no limit",
        min_value=0,
        value=0,
        step=100,
    )

    search_button = st.button("🔎 Search every day", type="primary", use_container_width=True)

with st.expander("What do I need to change?"):
    st.markdown(
        """
        **Normal use:** change the hotel, dates, nights and travellers in the sidebar.

        **Airport/destination IDs:** Glasgow (69) and Lanzarote (154) are already built in.
        For somewhere new, choose **Custom Jet2 ... ID** and paste the number from a Jet2
        search request. We can add proper named dropdowns as we collect the IDs.

        **Child ages matter:** enter the ages Jet2 should price for the holiday dates.
        """
    )

if search_button:
    if end_date < start_date:
        st.error("The latest departure must be on or after the earliest departure.")
        st.stop()

    if not durations:
        st.error("Choose at least one holiday length.")
        st.stop()

    if not hotel_name.strip():
        st.error("Enter a hotel name.")
        st.stop()

    total_searches = ((end_date - start_date).days + 1) * len(durations)
    if total_searches > 750:
        st.warning(
            f"That is {total_searches:,} date/duration checks. "
            "Try a shorter date range first so Jet2 does not throttle the search."
        )

    occupancy = build_occupancy(int(adults), [int(x) for x in child_ages], int(infants))
    board_id = BOARD_IDS[board]

    st.write(
        f"Searching **{hotel_name}** across **{total_searches:,}** "
        f"date/duration combinations…"
    )

    progress = st.progress(0)
    status = st.empty()

    rows = []
    errors = []
    completed = 0

    for departure in iter_dates(start_date, end_date):
        for duration in durations:
            status.write(f"Checking {departure:%d %b %Y} · {duration} nights")
            try:
                row = find_hotel_for_date(
                    hotel_name,
                    int(airport_id),
                    int(destination_id),
                    departure,
                    int(duration),
                    occupancy,
                    board_id,
                )
                if row:
                    if not max_price or row["Total price"] <= max_price:
                        rows.append(row)
            except Exception as exc:
                errors.append(f"{departure.isoformat()} / {duration} nights: {exc}")

            completed += 1
            progress.progress(min(completed / total_searches, 1.0))

            # Small pause to be polite to the live site and reduce throttling.
            time.sleep(0.15)

    status.empty()

    if not rows:
        st.warning("No matching All Inclusive prices were found for that search.")
        if errors:
            with st.expander("Technical errors"):
                st.code("\n".join(errors[:25]))
        st.stop()

    df = pd.DataFrame(rows)
    df["Difference vs cheapest"] = df["Total price"] - df["Total price"].min()
    df["Departure"] = pd.to_datetime(df["Departure"])

    cheapest = df.loc[df["Total price"].idxmin()]

    c1, c2, c3 = st.columns(3)
    c1.metric("Cheapest", f"£{cheapest['Total price']:,.0f}")
    c2.metric("Departure", cheapest["Departure"].strftime("%d %b %Y"))
    c3.metric("Nights", f"{int(cheapest['Nights'])}")

    display_df = df.sort_values(["Total price", "Departure"]).copy()
    display_df["Departure"] = display_df["Departure"].dt.strftime("%d/%m/%Y")

    st.subheader("Cheapest first")
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total price": st.column_config.NumberColumn("Total price", format="£%.0f"),
            "Difference vs cheapest": st.column_config.NumberColumn(
                "Vs cheapest", format="£%.0f"
            ),
            "Jet2 link": st.column_config.LinkColumn("Jet2"),
        },
    )

    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download results as CSV",
        data=csv,
        file_name="jet2_holiday_results.csv",
        mime="text/csv",
    )

    if errors:
        with st.expander(f"{len(errors)} checks had technical errors"):
            st.code("\n".join(errors[:50]))
