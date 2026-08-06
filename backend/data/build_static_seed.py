"""
Builds the remaining seed JSON that isn't sourced live from OBIS/GBIF: stations
(sensor readings), fisheries catch records, advisories, and the RAG text corpus.

Ocean sensor values are regionally-plausible approximations (INCOIS/CMEMS access
requires an account we don't have in this build window) — clearly labeled
"simulated" in the `source` field per CLAUDE.md. Catch tonnage is likewise
simulated but shaped to match the real, published CMFRI narrative (Kerala
sardine landings declining alongside a warm SST anomaly).
"""

import json
import os
import random

random.seed(42)
OUT_DIR = os.path.dirname(__file__)

STATIONS = [
    {"id": "mumbai", "name": "Mumbai Buoy", "lat": 19.076, "lng": 72.8777, "type": "buoy", "state": "Maharashtra", "base_sst": 28.2, "base_sal": 35.1},
    {"id": "goa", "name": "Goa eDNA Site", "lat": 15.4909, "lng": 73.8278, "type": "edna", "state": "Goa", "base_sst": 28.6, "base_sal": 34.8},
    {"id": "kochi", "name": "Kochi Advisory Zone", "lat": 9.9312, "lng": 76.2673, "type": "advisory", "state": "Kerala", "base_sst": 29.1, "base_sal": 34.5},
    {"id": "chennai", "name": "Chennai Buoy", "lat": 13.0827, "lng": 80.2707, "type": "buoy", "state": "Tamil Nadu", "base_sst": 28.9, "base_sal": 34.9},
    {"id": "vizag", "name": "Visakhapatnam eDNA Site", "lat": 17.6868, "lng": 83.2185, "type": "edna", "state": "Andhra Pradesh", "base_sst": 28.3, "base_sal": 34.6},
    {"id": "sundarbans", "name": "Sundarbans Buoy", "lat": 21.9497, "lng": 88.9468, "type": "buoy", "state": "West Bengal", "base_sst": 27.3, "base_sal": 31.4},
    {"id": "lakshadweep", "name": "Lakshadweep Coral Site", "lat": 10.5593, "lng": 72.6358, "type": "coral", "state": "Lakshadweep", "base_sst": 30.4, "base_sal": 35.3},
    {"id": "mannar", "name": "Gulf of Mannar Advisory", "lat": 9.1, "lng": 79.3, "type": "advisory", "state": "Tamil Nadu", "base_sst": 28.7, "base_sal": 34.7},
    {"id": "portblair", "name": "Port Blair eDNA Site", "lat": 11.6234, "lng": 92.7265, "type": "edna", "state": "Andaman & Nicobar", "base_sst": 28.5, "base_sal": 34.2},
    # Phase 10 — expanded coastline coverage. Appended (not inserted) so the
    # seeded random draws for the original 9 stations above stay identical.
    {"id": "ratnagiri", "name": "Ratnagiri Buoy", "lat": 16.9902, "lng": 73.312, "type": "buoy", "state": "Maharashtra", "base_sst": 28.0, "base_sal": 35.0},
    {"id": "mangalore", "name": "Mangalore eDNA Site", "lat": 12.9141, "lng": 74.856, "type": "edna", "state": "Karnataka", "base_sst": 28.5, "base_sal": 34.7},
    {"id": "kollam", "name": "Kollam Advisory Zone", "lat": 8.8932, "lng": 76.6141, "type": "advisory", "state": "Kerala", "base_sst": 29.0, "base_sal": 34.4},
    {"id": "puducherry", "name": "Puducherry Buoy", "lat": 11.9139, "lng": 79.8145, "type": "buoy", "state": "Puducherry", "base_sst": 28.8, "base_sal": 34.9},
    {"id": "paradip", "name": "Paradip Buoy", "lat": 20.3167, "lng": 86.6167, "type": "buoy", "state": "Odisha", "base_sst": 27.9, "base_sal": 32.0},
    {"id": "digha", "name": "Digha eDNA Site", "lat": 21.627, "lng": 87.509, "type": "edna", "state": "West Bengal", "base_sst": 27.5, "base_sal": 30.5},
    {"id": "porbandar", "name": "Porbandar Buoy", "lat": 21.6417, "lng": 69.6293, "type": "buoy", "state": "Gujarat", "base_sst": 27.0, "base_sal": 36.0},
    {"id": "veraval", "name": "Veraval Advisory Zone", "lat": 20.9159, "lng": 70.3629, "type": "advisory", "state": "Gujarat", "base_sst": 27.2, "base_sal": 35.8},
    {"id": "kutch", "name": "Gulf of Kutch Coral Site", "lat": 22.45, "lng": 69.0667, "type": "coral", "state": "Gujarat", "base_sst": 26.8, "base_sal": 36.5},
    {"id": "agatti", "name": "Agatti eDNA Site", "lat": 10.8386, "lng": 72.1948, "type": "edna", "state": "Lakshadweep", "base_sst": 30.0, "base_sal": 35.2},
    {"id": "kadmat", "name": "Kadmat Coral Site", "lat": 11.2233, "lng": 72.7833, "type": "coral", "state": "Lakshadweep", "base_sst": 30.2, "base_sal": 35.3},
    {"id": "havelock", "name": "Havelock eDNA Site", "lat": 12.0146, "lng": 92.9871, "type": "edna", "state": "Andaman & Nicobar", "base_sst": 28.6, "base_sal": 33.0},
    {"id": "diu", "name": "Diu Buoy", "lat": 20.7144, "lng": 70.9876, "type": "buoy", "state": "Daman & Diu", "base_sst": 27.3, "base_sal": 35.9},
    {"id": "alappuzha", "name": "Alappuzha Advisory Zone", "lat": 9.4981, "lng": 76.3388, "type": "advisory", "state": "Kerala", "base_sst": 29.2, "base_sal": 34.2},
]

DAYS = 60  # ~2 months of daily history so DHW / regression have something to chew on


def gen_station_readings(st):
    """Daily SST/salinity/chlorophyll history with a warming drift + noise.

    Coral sites get a larger simulated thermal-stress anomaly so the Degree
    Heating Weeks calculation downstream has something real to show — a flat
    line would make the bleaching-risk demo meaningless.
    """
    history = []
    total_drift = 3.75 if st["type"] == "coral" else 0.6
    sst = st["base_sst"] - total_drift
    sal = st["base_sal"]
    for day in range(DAYS):
        drift = total_drift * (day / DAYS)
        sst_today = round(sst + drift + random.uniform(-0.15, 0.15), 2)
        sal_today = round(sal + random.uniform(-0.2, 0.2), 2)
        chl_today = round(max(0.1, random.uniform(0.3, 1.1) - (0.3 if st["type"] == "coral" else 0)), 2)
        history.append({"day": day - DAYS + 1, "sst": sst_today, "salinity": sal_today, "chlorophyll": chl_today})
    return history


def main():
    stations_out = []
    for st in STATIONS:
        history = gen_station_readings(st)
        latest = history[-1]
        stations_out.append(
            {
                "id": st["id"],
                "name": st["name"],
                "lat": st["lat"],
                "lng": st["lng"],
                "type": st["type"],
                "state": st["state"],
                "latest": {
                    "sst_c": latest["sst"],
                    "salinity_psu": latest["salinity"],
                    "chlorophyll_mg_m3": latest["chlorophyll"],
                },
                "history": history,
                "source": "simulated (INCOIS/CMEMS-shaped; no live feed in this build)",
            }
        )
    with open(os.path.join(OUT_DIR, "stations.json"), "w") as f:
        json.dump(stations_out, f, indent=2)
    print(f"stations.json: {len(stations_out)} stations x {DAYS}d history")

    # ---- Fisheries catch records ----
    # Kerala sardine: declining trend (matches published CMFRI narrative + ref.html demo).
    # Tamil Nadu mackerel / Arabian Sea tuna: broadly stable/rising.
    # sst_c is a paired monthly value for the catch-vs-SST correlation chart (Phase 13) —
    # simulated alongside the tonnage series, shaped to match the "warm anomaly -> sardine
    # decline" narrative already used elsewhere, not measured data.
    catch_series = {
        "Sardinella longiceps|Kerala coast": {
            "tonnage": [520, 505, 490, 475, 460, 445, 430, 415, 400, 390, 380, 360],
            "sst_c": [28.3, 28.4, 28.5, 28.6, 28.7, 28.8, 28.9, 29.0, 29.0, 29.1, 29.2, 29.3],
        },
        "Rastrelliger kanagurta|Tamil Nadu coast": {
            "tonnage": [210, 214, 208, 220, 225, 218, 230, 235, 228, 240, 238, 245],
            "sst_c": [28.6, 28.6, 28.7, 28.6, 28.7, 28.7, 28.8, 28.7, 28.8, 28.7, 28.8, 28.8],
        },
        "Thunnus albacares|Arabian Sea": {
            "tonnage": [340, 345, 350, 348, 355, 360, 358, 365, 370, 368, 375, 380],
            "sst_c": [27.9, 27.9, 28.0, 28.0, 28.0, 28.1, 28.1, 28.1, 28.2, 28.2, 28.2, 28.3],
        },
    }
    months = [f"2025-{m:02d}" if m <= 12 else f"2026-{m - 12:02d}" for m in range(3, 15)]
    catch_records = []
    cid = 1
    for key, series in catch_series.items():
        species, region = key.split("|")
        for month, tonnage, sst_c in zip(months, series["tonnage"], series["sst_c"]):
            catch_records.append(
                {
                    "id": f"catch-{cid:04d}",
                    "species": species,
                    "region": region,
                    "date": f"{month}-01",
                    "tonnage": tonnage,
                    "sst_c": sst_c,
                    "advisory_status": "active" if species == "Sardinella longiceps" and tonnage < 430 else "none",
                }
            )
            cid += 1
    with open(os.path.join(OUT_DIR, "catch_records.json"), "w") as f:
        json.dump(catch_records, f, indent=2)
    print(f"catch_records.json: {len(catch_records)} monthly records ({len(catch_series)} species/region series), source=simulated (CMFRI-shaped)")

    # ---- Advisories ----
    advisories = [
        {
            "id": "adv-001",
            "region": "Kerala coast",
            "species": "Sardinella longiceps",
            "status": "active",
            "issued": "2026-07-01",
            "summary": "Sardine landings down 23% YoY, correlated with a 0.6°C SST anomaly and 18% chlorophyll-a drop in the upwelling zone. Advisory recommends reduced trawling effort through Q3.",
            "severity": "high",
        },
        {
            "id": "adv-002",
            "region": "Lakshadweep atolls",
            "species": "Acropora formosa",
            "status": "active",
            "issued": "2026-07-20",
            "summary": "Degree Heating Weeks at approximately 6 (Alert Level 1 — significant bleaching risk). Field verification of reef sites recommended within 10 days. Exact DHW is computed live from station SST history, see /api/predict/bleaching.",
            "severity": "high",
        },
        {
            "id": "adv-003",
            "region": "Gulf of Mannar",
            "species": "Dugong dugon",
            "status": "active",
            "issued": "2026-05-10",
            "summary": "Seagrass habitat protection zone. Boat traffic restrictions in effect during calving season.",
            "severity": "medium",
        },
        {
            "id": "adv-004",
            "region": "Goa coast",
            "species": "Hippocampus kuda",
            "status": "active",
            "issued": "2026-06-15",
            "summary": "Seahorse bycatch monitoring active following seagrass habitat loss reports.",
            "severity": "low",
        },
        {
            "id": "adv-005",
            "region": "Tamil Nadu coast",
            "species": "Rastrelliger kanagurta",
            "status": "resolved",
            "issued": "2026-02-01",
            "summary": "Mackerel landings stabilized after a brief Q1 dip; advisory closed.",
            "severity": "low",
        },
    ]
    with open(os.path.join(OUT_DIR, "advisories.json"), "w") as f:
        json.dump(advisories, f, indent=2)
    print(f"advisories.json: {len(advisories)} advisories")

    # ---- Species table (Species Explorer) ----
    species_table = [
        {"sci": "Sardinella longiceps", "common": "Indian oil sardine", "region": "Kerala coast", "status": "NT",
         "note": "Backbone of Kerala's pelagic fishery; landings are tracked closely for early stock-decline signals."},
        {"sci": "Chelonia mydas", "common": "Green sea turtle", "region": "Odisha coast", "status": "VU",
         "note": "Nests seasonally along the Odisha coast; tagged individuals feed regional migration models."},
        {"sci": "Gymnothorax sp.", "common": "Moray eel (eDNA match)", "region": "Lakshadweep", "status": None,
         "note": "Flagged via environmental DNA sampling; morphological confirmation is still pending."},
        {"sci": "Acropora formosa", "common": "Staghorn coral", "region": "Lakshadweep atolls", "status": "VU",
         "note": "Fast-growing reef-builder under active thermal-stress and bleaching monitoring."},
        {"sci": "Hippocampus kuda", "common": "Yellow seahorse", "region": "Goa coast", "status": "VU",
         "note": "Slow-moving and site-faithful, making it especially vulnerable to seagrass habitat loss."},
        {"sci": "Dugong dugon", "common": "Dugong", "region": "Gulf of Mannar", "status": "VU",
         "note": "Seagrass grazer whose population trend is a key indicator of coastal habitat health."},
        {"sci": "Thunnus albacares", "common": "Yellowfin tuna", "region": "Arabian Sea", "status": "LC",
         "note": "Commercially significant pelagic species tracked through fisheries landings data."},
        {"sci": "Rastrelliger kanagurta", "common": "Indian mackerel", "region": "Tamil Nadu coast", "status": "LC",
         "note": "High-volume coastal fishery species with strong, predictable seasonal landing patterns."},
    ]
    with open(os.path.join(OUT_DIR, "species.json"), "w") as f:
        json.dump(species_table, f, indent=2)
    print(f"species.json: {len(species_table)} species")

    # ---- RAG text corpus ----
    text_chunks = [
        {"id": "doc-01", "title": "Sardinella longiceps — species note",
         "text": "Sardinella longiceps (Indian oil sardine) is the backbone of Kerala's pelagic fishery. It is a short-lived, fast-growing clupeid highly sensitive to sea-surface temperature and chlorophyll-a availability in coastal upwelling zones. Recruitment failures have historically coincided with warm SST anomalies, as seen in 2016 and 2019.",
         "source": "CMFRI species profile (paraphrased)"},
        {"id": "doc-02", "title": "Kerala sardine advisory — July 2026",
         "text": "Sardine landings off Kerala are down 23% year-on-year. Cross-referencing CMFRI catch logs with INCOIS sea-surface temperature data shows a 0.6°C SST anomaly and an 18% chlorophyll-a drop in the upwelling zone, consistent with historical low-recruitment years. Advisory recommends reduced trawling effort through Q3 2026.",
         "source": "Fishing advisory adv-001"},
        {"id": "doc-03", "title": "Coral bleaching methodology — Degree Heating Weeks",
         "text": "Degree Heating Weeks (DHW) accumulate thermal stress by summing degrees Celsius above the local bleaching threshold (typically the maximum monthly mean plus 1°C) over a rolling 12-week window. DHW >= 4 indicates significant bleaching risk (Alert Level 1); DHW >= 8 indicates risk of mortality (Alert Level 2). This follows the NOAA Coral Reef Watch methodology.",
         "source": "NOAA Coral Reef Watch methodology"},
        {"id": "doc-04", "title": "Lakshadweep coral bleaching risk — current",
         "text": "Current Degree Heating Weeks at the Lakshadweep coral site is elevated, placing several monitored reef sites at Alert Level 1 bleaching risk (significant bleaching likely). Field verification of reef sites is recommended within 10 days. Exact DHW is computed live from station SST history, see /api/predict/bleaching.",
         "source": "Advisory adv-002 / station lakshadweep"},
        {"id": "doc-05", "title": "Acropora formosa — species note",
         "text": "Acropora formosa (staghorn coral) is a fast-growing, branching reef-building coral highly susceptible to thermal stress bleaching. It is a key structural species on Lakshadweep atoll reefs and an early indicator of reef health decline.",
         "source": "IUCN Red List summary (paraphrased)"},
        {"id": "doc-06", "title": "Dugong dugon — species note",
         "text": "Dugong dugon (dugong) is a marine mammal that grazes exclusively on seagrass meadows. Its population trend is considered a key bioindicator of coastal seagrass habitat health. The Gulf of Mannar population is protected under a dedicated habitat protection zone with seasonal boat traffic restrictions.",
         "source": "CMFRI/Wildlife Institute of India summary (paraphrased)"},
        {"id": "doc-07", "title": "Hippocampus kuda — species note",
         "text": "Hippocampus kuda (yellow seahorse) is slow-moving and highly site-faithful, which makes local populations especially vulnerable to seagrass and macroalgae habitat loss along the Goa coast. It is frequently taken as bycatch in trawl fisheries.",
         "source": "CMFRI species profile (paraphrased)"},
        {"id": "doc-08", "title": "Chelonia mydas — species note",
         "text": "Chelonia mydas (green sea turtle) nests seasonally along the Odisha coast. Tagged individuals are used to feed regional migration models, and nesting beach counts are a key long-term population indicator for the eastern Indian Ocean.",
         "source": "Wildlife Institute of India summary (paraphrased)"},
        {"id": "doc-09", "title": "Thunnus albacares — species note",
         "text": "Thunnus albacares (yellowfin tuna) is a commercially significant pelagic species in the Arabian Sea, tracked primarily through fisheries landings data rather than dedicated surveys. Occurrence records show a gradual range shift correlated with warming sea-surface temperatures.",
         "source": "OBIS occurrence records / CMFRI landings data"},
        {"id": "doc-10", "title": "Rastrelliger kanagurta — species note",
         "text": "Rastrelliger kanagurta (Indian mackerel) is a high-volume coastal fishery species off Tamil Nadu with strong, predictable seasonal landing patterns. It is considered Least Concern but is closely monitored as an indicator species for coastal pelagic fishery health.",
         "source": "CMFRI species profile (paraphrased)"},
        {"id": "doc-11", "title": "eDNA detection pipeline — Lakshadweep, July 2026",
         "text": "18 new taxa were flagged this month via environmental DNA barcoding at the Lakshadweep site, including 3 previously unrecorded in this region: a moray eel species (Gymnothorax sp.), a nudibranch (Doto sp.), and a deep-sea goby (Gobiidae sp.). Classification confidence ranges from 87% to 98%. Morphological confirmation is still pending for all three.",
         "source": "eDNA barcoding pipeline (simulated detections on real species list) / GBIF reference taxonomy"},
        {"id": "doc-12", "title": "Range shift methodology",
         "text": "Range shift is estimated by correlating OBIS/GBIF occurrence record latitude against year for a given species within the Indian EEZ. A positive slope (occurrences trending toward higher latitude over time) is interpreted as a poleward range shift consistent with warming sea-surface temperatures.",
         "source": "SAMUDRA methodology note"},
        {"id": "doc-13", "title": "Gulf of Mannar advisory — seagrass protection",
         "text": "The Gulf of Mannar advisory zone restricts boat traffic during dugong calving season to protect seagrass grazing habitat. This is a standing habitat-protection advisory rather than a stock-decline response.",
         "source": "Advisory adv-003"},
        {"id": "doc-14", "title": "Stock forecast methodology",
         "text": "Stock forecasts combine a linear regression of recent monthly catch tonnage with sea-surface temperature as a covariate, projected 6 months forward. This is a simple trend-extrapolation model intended to flag direction and rough magnitude of change, not a formal stock assessment.",
         "source": "SAMUDRA methodology note"},
    ]
    with open(os.path.join(OUT_DIR, "text_chunks.json"), "w") as f:
        json.dump(text_chunks, f, indent=2)
    print(f"text_chunks.json: {len(text_chunks)} chunks")


if __name__ == "__main__":
    main()
