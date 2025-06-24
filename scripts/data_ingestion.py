import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
import os

# --- Configuration ---
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
        return col[0].strip().lower().replace(' ', '_')
    else:
        return col.strip().lower().replace(' ', '_')

def fetch_and_store_price_data(engine):
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
            
            # Reset index to make Date a regular column
            data.reset_index(inplace=True)
            
            # Clean column names
            data.columns = [clean_column_name(col) for col in data.columns]
            
            # Add ticker column
            data['ticker'] = ticker
            
            # Create table name
            table_name = f"price_data_{ticker.lower()}"
            data.to_sql(table_name, engine, if_exists='replace', index=False)
            
            print(f"Successfully stored {len(data)} rows for {ticker} in table '{table_name}'.")
            
        except Exception as e:
            print(f"An error occurred for ticker {ticker}: {e}")
            import traceback
            traceback.print_exc()
    
    print("Data ingestion process finished.")

if __name__ == "__main__":
    # Create database connection
    db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    print(f"Connecting to database: {db_url}")
    
    try:
        engine = create_engine(db_url)
        # Test the connection
        with engine.connect() as conn:
            print("Database connection successful!")
        
        fetch_and_store_price_data(engine)
        
    except Exception as e:
        print(f"Database connection failed: {e}")
        import traceback
        traceback.print_exc()