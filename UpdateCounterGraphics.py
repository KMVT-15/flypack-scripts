from datetime import datetime
from os import path, getenv
from dotenv import load_dotenv
import requests
import csv

load_dotenv()

pfx = "UPDATE_COUNTER_GRAPHICS_"
COMPANION_URL = getenv(pfx + "COMPANION_URL")
CAPTIVATE_URL = getenv(pfx + "CAPTIVATE_URL")
SHEET_KEY = getenv(pfx + "SHEET_KEY")
SHEET_NAME = getenv(pfx + "SHEET_NAME")
ASSETS_DIR = getenv(pfx + "ASSETS_DIR")
FORCE_BUTTONS = getenv(pfx + "FORCE_BUTTONS").lower() == "true"
MAX_BUTTONS = int(getenv(pfx + "MAX_BUTTONS"))

def set_title_variable(title, variables):
    payload = {"action": "update", "title": title, "variables": variables}
    ok = False

    while not ok:
        try:
            resp = requests.post(f"{CAPTIVATE_URL}/api/", json=payload, timeout=50)
            ok = resp.json()["result"]["success"]
        except Exception as e:
            pass

    return resp.json()
 
def set_companion_variable(name, value):
    url = f"{COMPANION_URL}/api/custom-variable/{name}/value"
    resp = requests.post(url, json=value)

    return resp.text

def clean_row(row):
    return [ a.strip().replace("-","") for a in row ]

def title_to_path(t):
    return t.strip().replace(" ","").replace("/","").lower()

def columnize(lines):
    return [ list(col) for col in zip(*lines) ]

def fetch_sheets_data(key, sheet, region):
    url = f"https://docs.google.com/spreadsheets/d/{key}/gviz/tq?tqx=out:csv&sheet={sheet}&range={region}"
    resp = requests.get(url)
    reader = csv.reader(resp.text.splitlines())

    return [ clean_row(row) for row in reader ]

creds = fetch_sheets_data(SHEET_KEY, SHEET_NAME, "B4:C14")
schedule = fetch_sheets_data(SHEET_KEY, SHEET_NAME, "E4:F13")
metadata = fetch_sheets_data(SHEET_KEY, SHEET_NAME, "H4:J4")

location = metadata[0][0]
date = datetime.strptime(metadata[0][1], "%m/%d/%Y").date()
start_time = metadata[0][2]

creds_titles, creds_names = columnize(creds)
schedule_times, schedule_events = columnize(schedule)

location_button = {
    "title": f"Live At {location}",
    "img": path.join(ASSETS_DIR, "status", f"live at {title_to_path(location)}.png")
}

band_buttons = []

if not path.exists(location_button["img"]):
    img_name = path.basename(location_button["img"])
    print(f"WARNING: Missing location graphic '{img_name}'")

for event in schedule_events:
    p = path.join(ASSETS_DIR, "band logos", date.strftime("%Y%m%d"), title_to_path(event) + ".png")

    if not path.exists(p) and not FORCE_BUTTONS:
        img_name = path.basename(p)
        print(f"Skipping event graphic for '{event}'")
        continue

    band_buttons.append({
        "title": event,
        "img": p
    })

set_title_variable("Intermission", {
    "Times": "\n".join(schedule_times),
    "Events": "\n".join(schedule_events)
})

set_title_variable("Credits", {
    "Titles": "\n".join(creds_titles),
    "Names": "\n".join(creds_names)
})

if len(band_buttons) == 0:
    print("ERROR: No band logos found!")
    quit()

band_names = [ b["title"] for b in band_buttons ]
band_logos = [ b["img"] for b in band_buttons ]

set_companion_variable("band_names", band_names + [""] * (MAX_BUTTONS - len(band_names)))
set_companion_variable("band_logos", band_logos + [band_logos[-1]] * (MAX_BUTTONS - len(band_logos)))

set_companion_variable("location_name", location_button["title"])
set_companion_variable("location_logo", location_button["img"])

print("Done. Please check all graphics to ensure text does not overflow and that files are loaded.")
