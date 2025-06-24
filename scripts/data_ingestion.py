import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
import os  # Import the 'os' module

# --- Configuration is now read from Environment Variables ---
TICKERS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
PERIOD = '5y'
INTERVAL = '1d'

# --- Database Connection ---
# Read credentials from environment variables set by docker-compose
# The second argument is a default value, useful if you ever run it outside Docker
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost') # Default to 'localhost' but Docker will provide 'postgres'
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'finml_data')

db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(db_url)

# The rest of the script remains the same...

def clean_column_name(col):
    if isinstance(col, tuple):
        return col[0].strip().lower().replace(' ', '_')
    else:
        return col.strip().lower().replace(' ', '_')


# In scripts/data_ingestion.py

def fetch_and_store_price_data():
    print("Starting data ingestion process from within Docker...")

    for ticker in TICKERS:
        try:
            print(f"Fetching data for {ticker}...")
            data = yf.download(
                tickers=ticker,
                period=PERIOD,
                interval=INTERVAL,
                auto_adjust=True,
                group_by='column'
            )

            if data.empty:
                print(f"No data found for {ticker}. Skipping.")
                continue

            # ### THE FIX IS HERE ###
            # 1. Reset the index to make 'Date' a column.
            data.reset_index(inplace=True)
            
            # 2. Now clean ALL column names, including the new 'Date' column.
            data.columns = [clean_column_name(col) for col in data.columns]
            
            # 3. Add the ticker column.
            data['ticker'] = ticker

            table_name = f"price_data_{ticker.lower()}"
            data.to_sql(table_name, engine, if_exists='replace', index=False)
            print(f"Successfully stored data for {ticker} in table '{table_name}'.")

        except Exception as e:
            print(f"An error occurred for ticker {ticker}: {e}")
    print("Data ingestion process finished.")

if __name__ == "__main__":
    fetch_and_store_price_data()