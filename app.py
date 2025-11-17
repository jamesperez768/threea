import os
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime
from flask import Flask, render_template, request

API_KEY = "N5PWCYN7IHYNS1NU"

app = Flask(__name__)

def get_stock_symbols():
    """Reads stock symbols from the csv file."""
    try:
        df = pd.read_csv('stocks.csv')
        return sorted(df['Symbol'].tolist())
    except FileNotFoundError:
        return []

def get_api_function_name(time_series_key):
    """Maps the form value to the API function name."""
    mapping = {
        'TIME_SERIES_DAILY_ADJUSTED': ('Time Series (Daily)', '5. adjusted close'),
        'TIME_SERIES_WEEKLY': ('Weekly Time Series', '4. close'),
        'TIME_SERIES_MONTHLY': ('Monthly Time Series', '4. close'),
    }
    return mapping.get(time_series_key, (None, None))

@app.route('/', methods=['GET', 'POST'])
def index():
    stock_symbols = get_stock_symbols()
    chart_url, error = None, None

    selected_symbol = request.form.get('stock_symbol', stock_symbols[0] if stock_symbols else '')
    selected_chart_type = request.form.get('chart_type', 'line')
    selected_time_series = request.form.get('time_series', 'TIME_SERIES_DAILY_ADJUSTED')
    selected_start_date = request.form.get('start_date', '')
    selected_end_date = request.form.get('end_date', '')

    if request.method == 'POST':
        if API_KEY == "YOUR_API_KEY":
            error = "API Key is not set. Please edit app.py and add your Alpha Vantage API key."
        else:
            try:
                start_date = datetime.strptime(selected_start_date, '%Y-%m-%d')
                end_date = datetime.strptime(selected_end_date, '%Y-%m-%d')
            except ValueError:
                if end_date < start_date:
                    error = "Error: End date cannot be before the start date."
                    return render_template('index.html', **locals())

            api_series_name, api_close_key = get_api_function_name(selected_time_series)
            
            if not api_series_name:
                error = "Invalid time series selected."
                return render_template('index.html', **locals())

            url = f'https://www.alphavantage.co/query?function={selected_time_series}&symbol={selected_symbol}&apikey={API_KEY}'
            try:
                r = requests.get(url)
                r.raise_for_status()  
                data = r.json()

                if api_series_name not in data:
                    error = f"Could not retrieve data for symbol {selected_symbol}. Error: {data.get('Note') or data.get('Error Message', 'Unknown API error')}"
                else:
                    df = pd.DataFrame.from_dict(data[api_series_name], orient='index')
                    df.index = pd.to_datetime(df.index)
                    
                    mask = (df.index >= start_date) & (df.index <= end_date)
                    filtered_df = df.loc[mask]

                    if filtered_df.empty:
                        error = "No data available for the selected date range."
                    else:
                        filtered_df[api_close_key] = pd.to_numeric(filtered_df[api_close_key])

                        plt.figure(figsize=(12, 6))
                        if selected_chart_type == 'bar':
                            plt.bar(filtered_df.index, filtered_df[api_close_key])
                        else:
                            plt.plot(filtered_df.index, filtered_df[api_close_key])
                        
                        plt.title(f'{selected_symbol} Stock Price ({start_date.date()} to {end_date.date()})')
                        plt.xlabel('Date')
                        plt.ylabel('Adjusted Close Price (USD)')
                        plt.grid(True)
                        plt.xticks(rotation=45)
                        plt.tight_layout()

                        static_dir = os.path.join(app.root_path, 'static', 'images')
                        os.makedirs(static_dir, exist_ok=True) 
                        chart_path = os.path.join(static_dir, 'stock_chart.png')
                        plt.savefig(chart_path)
                        plt.close()

                        chart_url = f'/static/images/stock_chart.png?t={datetime.now().timestamp()}'

            except requests.exceptions.RequestException as e:
                error = f"Network error: {e}"
            except Exception as e:
                error = f"An unexpected error occurred: {e}"

    return render_template('index.html', **locals())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)