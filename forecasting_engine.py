# forecasting_engine.py

import pandas as pd
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPICallError

def get_sales_forecast(project_id: str, dataset_id: str, table_id: str) -> pd.DataFrame:
    """
    Creates a forecasting model in BigQuery ML and uses it to predict sales.

    Args:
        project_id: Your Google Cloud project ID.
        dataset_id: The BigQuery dataset ID where your table and model reside.
        table_id: The BigQuery table ID containing the historical sales data.

    Returns:
        A pandas DataFrame with the forecasted sales data.
    """
    client = bigquery.Client(project=project_id)
    model_id = f"{project_id}.{dataset_id}.sales_forecasting_model"
    
    # SQL to create the ARIMA_PLUS model. It will only create if it doesn't exist.
    create_model_query = f"""
    CREATE OR REPLACE MODEL `{model_id}`
    OPTIONS(
        model_type='ARIMA_PLUS',
        time_series_timestamp_col='Date',
        time_series_data_col='Sales_Volume',
        time_series_id_col='Product_Category',
        auto_arima_max_order=5
    ) AS
    SELECT
        Date,
        Product_Category,
        Sales_Volume
    FROM
        `{project_id}.{dataset_id}.{table_id}`
    """

    # SQL to run the forecast using the created model
    forecast_query = f"""
    SELECT
        *
    FROM
        ML.FORECAST(MODEL `{model_id}`,
                    STRUCT(30 AS horizon, 0.8 AS confidence_level))
    """

    try:
        # --- Step 1: Create the model ---
        print("Creating or replacing BigQuery ML model...")
        create_job = client.query(create_model_query)
        create_job.result()  # Wait for the job to complete
        print(f"Model '{model_id}' created successfully.")

        # --- Step 2: Run the forecast ---
        print("Generating forecast...")
        forecast_df = client.query(forecast_query).to_dataframe()
        print("Forecast generated successfully.")
        
        # Convert forecast_timestamp to datetime for plotting
        forecast_df['forecast_timestamp'] = pd.to_datetime(forecast_df['forecast_timestamp'])

        return forecast_df

    except GoogleAPICallError as e:
        print(f"An error occurred with the BigQuery API: {e}")
        return pd.DataFrame() # Return empty dataframe on error