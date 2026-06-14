#!/usr/bin/env python
# coding: utf-8

# In[1]:


"""
San Diego Weather Helper for Photographers — Production ETL & Data Quality Pipeline
---------------------------------------------------------------------------------
Course Focus: Data Quality Engineering & Aggregated Transformation Layers

Description:
    An automated, modular data pipeline that extracts weather metrics, performs raw 
    integrity checks, normalizes mixed formats, calculates custom photographer light 
    quality and styling safety indices, and implements an idempotent data warehouse load strategy.

Required packages:
    pip install pandas sqlalchemy psycopg2-binary python-dotenv
"""


# In[2]:


from __future__ import annotations


# In[3]:


import logging
import os
import re
import sys
from datetime import datetime, date, time
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.types import Integer, String, Float, DateTime, Date


# In[4]:


BASE_DIR = Path(__file__).resolve().parent if "__file__" in locals() else Path.cwd()
WEATHER_DATA_CSV = BASE_DIR / "open-meteo-32.72N117.15W12m.csv"


# In[5]:


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "etl_execution.log"),
        logging.StreamHandler(sys.stdout)])


# In[6]:


logger = logging.getLogger("WeatherETLPipeline")


# In[7]:


def get_database_url() -> str:
    """Safely extracts database connection properties from context environment."""
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")

    if not password:
        logger.critical("Database configuration missing from environment.")
        raise RuntimeError("Define DB_PASSWORD or DATABASE_URL inside your .env configuration file.")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"


# In[8]:


def extract_source_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extracts weather payload data segments from the target storage location.
    Conforms to slide guidelines by isolating text and structural matrix frames.
    """
    logger.info(f"Initiating extraction sequence from file source: {WEATHER_DATA_CSV.name}")
    try:
        if not WEATHER_DATA_CSV.exists():
            raise FileNotFoundError(f"Source data file targets missing at: {WEATHER_DATA_CSV}")

        df_current_raw = pd.read_csv(WEATHER_DATA_CSV, skiprows=3, nrows=1)
        
        df_daily_raw = pd.read_csv(WEATHER_DATA_CSV, skiprows=6)

        logger.info(f"Extraction successful. Current rows: {len(df_current_raw)}, Daily rows: {len(df_daily_raw)}")
        return df_current_raw, df_daily_raw

    except Exception as e:
        logger.error(f"Extraction step failed catastrophically: {str(e)}")
        raise


# In[9]:


def validate_raw_inputs(current_df: pd.DataFrame, daily_df: pd.DataFrame) -> bool:
    """
    Executes structural integrity gatekeeping checks before modifications.
    Validates structural dimensions, missing properties, and schemas early.
    """
    logger.info("Executing initial input layer data validation suite...")
    try:
        if current_df.empty or daily_df.empty:
            logger.error("Validation Error: Input frames are empty.")
            return False

        expected_daily_cols = ['time', 'weather_code (wmo code)', 'temperature_2m_max (°C)']
        for col in expected_daily_cols:
            if col not in daily_df.columns:
                logger.error(f"Validation Error: Expected raw property structural index column missing: '{col}'")
                return False

        logger.info("Stage 1 Data Validation passed. Structural dimensions verified.")
        return True
    except Exception as e:
        logger.error(f"Error encountered during pre-load inspection: {str(e)}")
        return False


# In[10]:


def clean_and_normalize(current_raw: pd.DataFrame, daily_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Handles null profiles, drops duplications, standardizes casing and labels,
    and converts weather data configurations into consistent imperial layouts.
    """
    logger.info("Beginning data cleaning and attribute normalization phase...")
    try:
        curr_df = current_raw.copy()
        daily_df = daily_raw.copy()

        daily_df = daily_df.drop_duplicates(subset=['time'])

        curr_df.rename(columns={
            "time": "read_time", "temperature_2m (°C)": "temperature_2m",
            "relative_humidity_2m (%)": "relative_humidity_2m", "apparent_temperature (°C)": "apparent_temperature",
            "precipitation (mm)": "precipitation", "weather_code (wmo code)": "weather_code_id",
            "cloud_cover (%)": "cloud_cover", "wind_speed_10m (km/h)": "wind_speed_10m"
        }, inplace=True)

        daily_df.rename(columns={
            "time": "forecast_date", "weather_code (wmo code)": "weather_code_id",
            "temperature_2m_max (°C)": "temperature_2m_max", "temperature_2m_min (°C)": "temperature_2m_min",
            "sunrise (iso8601)": "sunrise", "sunset (iso8601)": "sunset",
            "precipitation_sum (mm)": "precipitation_sum", "wind_speed_10m_max (km/h)": "wind_speed_10m_max"
        }, inplace=True)

        curr_df["read_time"] = pd.to_datetime(curr_df["read_time"])
        daily_df["forecast_date"] = pd.to_datetime(daily_df["forecast_date"]).dt.date
        daily_df["sunrise"] = pd.to_datetime(daily_df["sunrise"])
        daily_df["sunset"] = pd.to_datetime(daily_df["sunset"])

        for df in [curr_df, daily_df]:
            for col in df.columns:
                if "temperature" in col:
                    df[col] = (df[col] * 9/5) + 32
                elif "precipitation" in col:
                    df[col] = df[col] / 25.4
                elif "wind_speed" in col:
                    df[col] = df[col] / 1.60934

        logger.info("Cleaning and conversion computations finished successfully.")
        return curr_df, daily_df

    except Exception as e:
        logger.error(f"Error encountered during cleaning transformations: {str(e)}")
        raise


# In[11]:


def compute_derived_metrics(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs analytical value-add derived dimensions and rule constraints
    specifically designed to optimize downstream Power BI dashboard queries.
    """
    logger.info("Computing derived metrics and photoshoot optimization profiles...")
    try:
        df = daily_df.copy()

        df["diurnal_temperature_range"] = df["temperature_2m_max"] - df["temperature_2m_min"]

        df["daylight_hours_delta"] = (pd.to_datetime(df["sunset"]) - pd.to_datetime(df["sunrise"])).dt.total_seconds() / 3600.0

        df["is_beach_portrait_safe"] = (df["wind_speed_10m_max"] < 12.0) & (df["precipitation_sum"] == 0.0)

        df["requires_indoor_studio_backup"] = (df["precipitation_sum"] > 0.05) | (df["temperature_2m_max"] > 85.0)

        logger.info("Derived structural transformation analytics completed successfully.")
        return df
    except Exception as e:
        logger.error(f"Error encountered during analytics metric generation: {str(e)}")
        raise


# In[12]:


def check_processed_data_quality(daily_df: pd.DataFrame) -> bool:
    """
    Implements mandatory Quality Engineering validation rule boundaries.
    Catches out-of-bounds metrics, duplicate dates, or broken fields early.
    """
    logger.info("Running Stage 2 Data Quality Engineering sanity checks...")
    try:
        if daily_df["forecast_date"].duplicated().any():
            logger.error("Data Quality Failure: Critical Primary Key duplicates observed on forecast timeline rows.")
            return False

        null_counts = daily_df.isnull().sum().sum()
        if null_counts > 0:
            logger.error(f"Data Quality Failure: Observed {null_counts} unexpected null items in clean schema layer.")
            return False

        if (daily_df["temperature_2m_max"] > 120.0).any() or (daily_df["temperature_2m_min"] < 20.0).any():
            logger.warning("Data Quality Warning: Extreme ambient out-of-bounds temperature anomalies caught.")

        logger.info("Data Quality Engineering validation rules successfully cleared.")
        return True
    except Exception as e:
        logger.error(f"Quality inspection encountered an error state: {str(e)}")
        return False


# In[13]:


def load_datasets_incrementally(engine, current_df: pd.DataFrame, daily_df: pd.DataFrame) -> None:
    """
    Executes an idempotent incremental database load strategy.
    Prevents duplications by matching records against existing primary key dates.
    """
    logger.info("Initiating database incremental loading sequence...")
    try:
        create_reference_tables_if_missing(engine)

        with engine.begin() as connection:
            current_df.to_sql(
                name="current_weather", con=connection, if_exists="append",
                index=False, schema="public", method="multi",
                dtype={"read_time": DateTime(), "temperature_2m": Float(), "weather_code_id": Integer()}
            )
            logger.info("Transaction tracking row added to table: current_weather.")

            existing_dates = set()
            table_check = connection.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'daily_forecast');"
            )).fetchone()[0]

            if table_check:
                db_dates = connection.execute(text("SELECT forecast_date FROM public.daily_forecast;")).fetchall()
                existing_dates = {row[0] for row in db_dates}

            new_records_df = daily_df[~daily_df["forecast_date"].isin(existing_dates)]

            if not new_records_df.empty:
                new_records_df.to_sql(
                    name="daily_forecast", con=connection, if_exists="append",
                    index=False, schema="public", method="multi",
                    dtype={
                        "forecast_date": Date(), "weather_code_id": Integer(),
                        "temperature_2m_max": Float(), "temperature_2m_min": Float(),
                        "is_beach_portrait_safe": Boolean(), "requires_indoor_studio_backup": Boolean()
                    }
                )
                logger.info(f"Incremental load complete. Added {len(new_records_df)} new forecast rows.")
            else:
                logger.info("Incremental Load check complete: 0 new rows processed. Duplicate rows ignored.")

    except Exception as e:
        logger.error(f"Database operation crashed during table write tracking: {str(e)}")
        raise


# In[14]:


def create_reference_tables_if_missing(engine) -> None:
    """Ensures base weather definitions match primary structural specifications."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS public.weather_code (
        weather_code_id INTEGER PRIMARY KEY,
        description TEXT NOT NULL
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))
        
        check_count = conn.execute(text("SELECT COUNT(*) FROM public.weather_code;")).fetchone()[0]
        if check_count == 0:
            records = [
                {"id": 0, "d": "Clear sky"}, {"id": 1, "d": "Mainly clear"},
                {"id": 2, "d": "Partly cloudy"}, {"id": 3, "d": "Overcast"},
                {"id": 45, "d": "Foggy"}
            ]
            for r in records:
                conn.execute(text("INSERT INTO public.weather_code VALUES (:id, :d);"), {"id": r["id"], "d": r["d"]})


# In[17]:


def main() -> None:
    """Orchestrates the entire production data workflow pipeline sequence."""
    logger.info("==================================================")
    logger.info("STARTING WEATHER PIPELINE RUN")
    logger.info("==================================================")
    try:
        db_url = "postgresql+psycopg2://postgres:your_actual_password@localhost:5432/postgres"
        engine = create_engine(db_url)

        raw_current, raw_daily = extract_source_data()

        if not validate_raw_inputs(raw_current, raw_daily):
            logger.critical("Pipeline aborted due to structural format failures at input layer.")
            sys.exit(1)

        clean_curr, clean_daily = clean_and_normalize(raw_current, raw_daily)

        processed_daily = compute_derived_metrics(clean_daily)

        if not check_processed_data_quality(processed_daily):
            logger.critical("Pipeline aborted due to high data volume anomalies or duplicated targets.")
            sys.exit(1)

        load_datasets_incrementally(engine, clean_curr, processed_daily)

        logger.info("==================================================")
        logger.info("WEATHER PIPELINE WORKFLOW EXECUTION SUCCESSFUL")
        logger.info("==================================================")

    except Exception as e:
        logger.critical(f"ETL Execution sequence broke due to critical exceptions: {str(e)}")
        sys.exit(1)

