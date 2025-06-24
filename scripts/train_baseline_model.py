import pandas as pd
import mlflow
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
    """Creates an EXTENDED set of time-series features from the price data."""
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # --- NEW: Longer-term Moving Averages ---
    df['ma_5'] = df['close'].rolling(window=5).mean()
    df['ma_10'] = df['close'].rolling(window=10).mean() # New
    df['ma_20'] = df['close'].rolling(window=20).mean()
    df['ma_50'] = df['close'].rolling(window=50).mean() # New
    
    # --- NEW: Price Rate of Change ---
    df['roc_10'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100 # New
    
    # Volatility
    df['volatility'] = df['close'].rolling(window=20).std()
    
    # --- NEW: More Lag features ---
    for i in range(1, 11): # Extended from 5 to 10
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
    """Loads, processes, trains, evaluates, and LOGS a model for a single ticker."""
    print(f"\n--- Processing Ticker: {ticker.upper()} ---")
    
    table_name = f"price_data_{ticker}"
    
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        df = feature_engineering(df.copy())
        df = create_target_variable(df.copy())
        
        if df.empty:
            print(f"Not enough data for {ticker} after processing. Skipping.")
            return

        features = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume', 'ticker', 'price_change', 'target']]
        X = df[features]
        y = df['target']
        
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]

        # ### START OF MLFLOW INTEGRATION ###
        # Set the experiment name. If it doesn't exist, MLflow creates it.
        mlflow.set_experiment("Baseline XGBoost Training")
        
        with mlflow.start_run(run_name=f"extended_features_{ticker}"):
            print(f"Starting MLflow run for {ticker.upper()}")
            
            # 1. Log parameters
            params = {
                'n_estimators': 100,
                'learning_rate': 0.1,
                'max_depth': 3,
                'train_size': len(X_train),
                'test_size': len(X_test),
                'ticker': ticker
            }
            mlflow.log_params(params)
            
            # Train the model (code is the same)
            model = xgb.XGBClassifier(
                objective='binary:logistic',
                eval_metric='logloss',
                use_label_encoder=False,
                n_estimators=params['n_estimators'],
                learning_rate=params['learning_rate'],
                max_depth=params['max_depth']
            )
            model.fit(X_train, y_train)
            
            # Make predictions
            y_pred = model.predict(X_test)
            
            # 2. Log metrics
            accuracy = accuracy_score(y_test, y_pred)
            report = classification_report(y_test, y_pred, output_dict=True)
            
            mlflow.log_metric("accuracy", accuracy)
            mlflow.log_metric("precision_class_1", report['1']['precision'])
            mlflow.log_metric("recall_class_1", report['1']['recall'])
            mlflow.log_metric("f1_score_class_1", report['1']['f1-score'])

            # 3. Log the model itself as an artifact
            mlflow.xgboost.log_model(model, artifact_path=f"model_{ticker}")
            
            print(f"Successfully logged run for {ticker.upper()} to MLflow.")

    except Exception as e:
        print(f"An error occurred while processing {ticker}: {e}")

if __name__ == "__main__":
    for ticker in tqdm(TICKERS, desc="Training models for all tickers"):
        train_model_for_ticker(ticker)