import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
import os
import sys

# --- Configuration (remains the same) ---
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'finml_data')

TICKERS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
PERIOD = '5y'
INTERVAL = '1d'

def clean_column_name(col):
    if isinstance(col, tuple):
        return col[0].strip().lower().replace(' ', '')
    else:
        return col.strip().lower().replace(' ', '')

# SIMPLIFIED: Function now accepts the engine object
def fetch_and_store_price_data(engine):
    print("Starting data ingestion process from within Docker...")
    errors_found = False
    for ticker in TICKERS:
        try:
            print(f"Fetching data for {ticker}...")
            data = yf.download(
                tickers=ticker, period=PERIOD, interval=INTERVAL,
                auto_adjust=True, group_by='column'
            )

            if data.empty:
                print(f"No data found for {ticker}. Skipping.")
                continue

            data.reset_index(inplace=True)
            data.columns = [clean_column_name(col) for col in data.columns]
            data['ticker'] = ticker
            table_name = f"price_data_{ticker.lower()}"

            # SIMPLIFIED: Pass the engine directly. This is the correct way with compatible libraries.
            data.to_sql(table_name, engine, if_exists='replace', index=False)

            print(f"Successfully stored {len(data)} rows for {ticker} in table '{table_name}'.")
        except Exception as e:
            print(f"An error occurred for ticker {ticker}: {e}")
            import traceback
            traceback.print_exc()
            errors_found = True

    print("Data ingestion process finished.")
    if errors_found:
        print("Errors were found during ingestion. Exiting with failure code.")
        sys.exit(1)


if __name__ == "__main__":
    db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    print(f"Connecting to database: {db_url}")

    try:
        engine = create_engine(db_url)
        # Test the connection just to be sure
        with engine.connect() as conn:
            print("Database connection successful!")
        
        # Pass the engine to the function
        fetch_and_store_price_data(engine)

    except Exception as e:
        print(f"Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)