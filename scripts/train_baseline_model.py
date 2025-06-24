import pandas as pd
from sqlalchemy import create_engine
import os
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from tqdm import tqdm

# --- Database Connection (Same as ingestion script) ---
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'finml_data')
db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(db_url)

TICKERS = ['aapl', 'googl', 'msft', 'tsla'] # Use lowercase tickers as per our table names

def feature_engineering(df):
    """Creates time-series features from the price data."""
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Simple Moving Averages
    df['ma_5'] = df['close'].rolling(window=5).mean()
    df['ma_20'] = df['close'].rolling(window=20).mean()
    
    # Volatility
    df['volatility'] = df['close'].rolling(window=20).std()
    
    # Lag features
    for i in range(1, 6):
        df[f'lag_{i}'] = df['close'].shift(i)
        
    df.dropna(inplace=True)
    return df

def create_target_variable(df):
    """Creates the binary target variable: 1 if next day's close is higher, else 0."""
    df['price_change'] = df['close'].diff()
    df['target'] = (df['price_change'].shift(-1) > 0).astype(int)
    
    # We drop the last row because it will have a NaN target
    df.dropna(inplace=True)
    return df

def train_model_for_ticker(ticker):
    """Loads, processes, trains, and evaluates a model for a single ticker."""
    print(f"\n--- Processing Ticker: {ticker.upper()} ---")
    
    table_name = f"price_data_{ticker}"
    
    try:
        # 1. Load Data
        print(f"Loading data from table: {table_name}")
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        
        # 2. Feature Engineering
        print("Engineering features...")
        df = feature_engineering(df.copy())
        
        # 3. Create Target Variable
        print("Creating target variable...")
        df = create_target_variable(df.copy())
        
        if df.empty:
            print(f"Not enough data for {ticker} after processing. Skipping.")
            return

        # 4. Define Features (X) and Target (y)
        features = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume', 'ticker', 'price_change', 'target']]
        X = df[features]
        y = df['target']
        
        # 5. Split Data (Time-series split, not random!)
        # We must not shuffle time-series data to avoid lookahead bias.
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        print(f"Training on {len(X_train)} samples, testing on {len(X_test)} samples.")
        
        # 6. Train XGBoost Model
        print("Training XGBoost model...")
        model = xgb.XGBClassifier(
            objective='binary:logistic',
            eval_metric='logloss',
            use_label_encoder=False,
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3
        )
        model.fit(X_train, y_train)
        
        # 7. Evaluate Model
        print("Evaluating model...")
        y_pred = model.predict(X_test)
        
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Accuracy for {ticker.upper()}: {accuracy:.4f}")
        print("Classification Report:")
        print(classification_report(y_test, y_pred))
        print("Confusion Matrix:")
        print(confusion_matrix(y_test, y_pred))
        
    except Exception as e:
        print(f"An error occurred while processing {ticker}: {e}")

if __name__ == "__main__":
    for ticker in tqdm(TICKERS, desc="Training models for all tickers"):
        train_model_for_ticker(ticker)