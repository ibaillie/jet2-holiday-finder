# Jet2 Holiday Finder

A small private Streamlit app for comparing live Jet2holidays package prices across every departure day in a date range.

## What it does

- Searches every day between two dates
- Supports several holiday lengths
- Lets you enter adults, child ages and infants
- Finds a specific hotel by full or partial name
- Currently supports **All Inclusive** price comparison
- Shows hotel/resort, room, rating, TripAdvisor score, total price, discount, availability and a Jet2 link
- Sorts results cheapest first
- Downloads results as CSV

## Built-in IDs

These are directly verified from Jet2 searches:

- Glasgow airport: **69**
- Lanzarote destination area: **154**

For another airport or destination, choose **Custom Jet2 ... ID** in the app. More named options can be added later as we collect/verify the IDs.

## Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click **Create app**
4. Choose this repository: `ibaillie/jet2-holiday-finder`
5. Branch: `main`
6. Main file path: `app.py`
7. Deploy

The app will install the packages in `requirements.txt` automatically.

## Notes

This is an unofficial personal comparison tool. Jet2's website/API can change at any time, which may require the app to be updated.

The app deliberately pauses briefly between checks to reduce load on the live site. Very large date ranges can take a while.

## Usual search

For the existing Lanzarote benchmark:

- Airport: Glasgow
- Destination: Lanzarote
- Hotel: Iberostar Selection Lanzarote Park
- Board: All Inclusive
- Travellers: 2 adults, one child age 4, one infant
