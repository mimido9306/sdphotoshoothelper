# San Diego Photoshoot Helper

## System Architecture & Tech Stack
* **Data Source:** Open-Meteo Climatological REST API (Targeting the primary San Diego Coordinate Node: 32.72° N, 117.15° W, at a 12m coastal elevation envelope).
* **ETL Engine:** Python 3.13 / Pandas Dataframe Core
* **Data Warehouse:** Supabase Cloud PostgreSQL Relational Database Instance. This serves as the persistent, centralized operational data store for historical and upcoming forecast blocks.
* **Front-End Presentation Layer:** Power BI Desktop Visual Analytics MVP. Connected directly via Web REST APIs to pull real-time database rows streaming from the cloud.


## How to Run the Dashboard
Step 1: Run the Backend Python ETL Pipeline

* Clone this repository to your machine and place your target coordinate weather source file (open-meteo-32.72N117.15W12m.csv) directly in your project folder.
* Open your preferred notebook environment and open Schema.ipynb.
* Select "Run All Cells".
* The script will automatically execute data quality validation suites, compute derived metrics, and push the forecast rows live to the cloud. Look for the final terminal confirmation log entry: [INFO] Incremental load complete. Added new forecast rows.
[INFO] WEATHER PIPELINE WORKFLOW EXECUTION SUCCESSFUL

Step 2: Supabase Cloud Storage
* Log into your Supabase Console
* Navigate to the Table Editor view
* Select your active weather data table to view the freshly populated rows, structural timestamps, and computed safety boolean metrics securely stored on the cloud server

Step 3: Launch the Weather Dashboard
* Launch Power BI Desktop
* Open the file ShutterWeather_Dashboard.pbix
* Click the Refresh button on the top home ribbon to instantly fetch the newly uploaded database rows streaming from the Supabase cloud


## Dependencies and Installation
To initialize the backend data engine environment, ensure you have Python 3.13+ installed. Navigate to the root directory of your project repository and install the verified tracking library stack:

bash
pip install pandas psycopg2-binary sqlalchemy openpyxl requests

## Business Insights
The objective of the Photoshoot Helper is to eliminate the inconvenience and financial stress that comes with unpredictable photoshoot interruptions. Outdoor sessions are heavily impacted by wind and water; high-end lighting softboxes act like kites in strong coastal gusts, risking serious equipment damage, while high humidity or light rain instantly ruins professional client hair and makeup:

To solve this, the Python pipeline processes raw incoming metrics through programmatic logic gates:

* Beach photoshoot safety: Photo sessions on the San Diego coastline are labeled unsafe if peak sustained wind gusts surpass threshold safety envelopes or if any precipitation sum drops above 0.00 in.
* Studio Backup: If temperature ranges collapse below comfortable posing minimums or if precipitation models signal imminent rain, the system flags the booking window as requiring an immediate indoor studio backup

* By centralizing these indicators onto an interactive executive dashboard, booking coordinators can monitor the upcoming 7-day schedule at a single glance. Instead of reactionary, morning-of cancellations that leave photographers uncompensated and clients frustrated, studio managers use the conditional formatting alerts on the table matrix to execute data-driven pivots 48 to 72 hours in advance. Clients scheduled on unsafe costal days are seamlessly rerouted into pre-booked indoor rental studios or proactively moved to high-suitability calendar slots. preserving studio revenue and maximizing team utility.
