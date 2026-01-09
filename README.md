# Singapore GTFS Data (2026) 🚌🚇

> **Note:** This is a **Vibecode learning project** created to understand how to build and update GTFS feeds programmatically.

This repository provides a fully updated **General Transit Feed Specification (GTFS)** for Singapore, generated in **January 2026** and valid through **2030**.

It serves as a massive update to the original [singapore-gtfs](https://github.com/yinshanyang/singapore-gtfs) repository by **yinshanyang**, which provided the foundation and inspiration for this work. Kudos to the original author! 👏

## 📥 Download Data
[**Download singapore-gtfs.zip**](./singapore-gtfs.zip) (314 MB)

---

## ✨ What's New?
The AI rebuilt the feed from the ground up to reflect the latest transport network:

- **📅 Full 7-Day Schedule**: Expanded on the original weekday coverage to now include complete schedules for **Weekdays, Saturdays, and Sundays**.
- **🚇 New MRT Stations**: Fully updated to include:
  - **Punggol Coast (NE18)**
  - Full **Thomson-East Coast Line (TEL)** (TE1 - TE29)
- **🚌 Complete Bus Network**: Over **230,000 trips** generated directly from the latest [LTA DataMall](https://datamall.lta.gov.sg/) data.
- **✅ Specialized Validation**:
  - **Physics Enforcement**: Implements **Haversine distance checks** to enforce a maximum bus speed of 80km/h, automatically correcting data where source distances were missing or invalid.
  - **Standards Compliance**: All route colors are now proper **Hex codes**, and direction IDs are normalized to GTFS standards (0/1).
  - **Data Integrity**: Cleaned foreign key references and validated against the official MobilityData GTFS Validator.

## 🛠️ How It Works
The data is generated using Python scripts that combine official API data with community sources:

1.  **Bus Data**: Fetched directly from LTA DataMall (Services, Routes, Stops).
2.  **MRT Data**: Station locations sourced from [cheeaun/sgraildata](https://github.com/cheeaun/sgraildata), with synthetic schedules generated based on realistic operating hours (05:30 - 23:30) and frequencies (3-6 mins).

## 👩‍💻 Usage
You can use the `singapore-gtfs.zip` directly in any GTFS-compatible application (OpenTripPlanner, Google Maps, etc.).

### Want to regenerate it yourself?
1.  Get an API Key from [LTA DataMall](https://datamall.lta.gov.sg/).
2.  Set it as an environment variable: `export LTA_ACCOUNT_KEY="your_key"`
3.  Run the scripts:
    ```bash
    python3 download_lta_data.py  # DLs fresh data
    python3 generate_gtfs.py      # Builds the ZIP
    ```

## ⚠️ Limitations
- **Synthetic MRT Schedules**: Exact train timings are not public, so typical frequencies are used.
- **Estimated Bus Times**: Travel times between stops are estimated based on distance.

## License
Data is derived from [LTA DataMall](https://datamall.lta.gov.sg/) under the [Singapore Open Data Licence](https://data.gov.sg/open-data-licence).
