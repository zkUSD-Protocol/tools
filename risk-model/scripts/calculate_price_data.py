import pandas as pd
import numpy as np


def calculate_price_drops(csv_path):
    # Read the CSV file
    df = pd.read_csv(csv_path)

    # Convert snapped_at to datetime
    df['snapped_at'] = pd.to_datetime(df['snapped_at'])

    # Sort by date to ensure chronological order
    df = df.sort_values('snapped_at')

    # Dictionary to store results
    results = {}

    # Calculate drops for different time periods (1-7 days)
    for days in range(1, 8):
        # Calculate price changes over the specified period
        df[f'{days}d_price_change'] = df['price'].diff(periods=days)
        df[f'{days}d_price_change_pct'] = df['price'].pct_change(periods=days)

        # Find the largest drop (minimum change is maximum drop)
        max_drop = df[f'{days}d_price_change'].min()
        max_drop_pct = df[f'{days}d_price_change_pct'].min() * 100

        # Find the date when the maximum drop occurred
        max_drop_date = df.loc[df[f'{days}d_price_change']
                               == max_drop, 'snapped_at'].iloc[0]

        # Store results
        results[f'{days}_day'] = {
            'max_drop_absolute': abs(max_drop),
            'max_drop_percentage': abs(max_drop_pct),
            'date': max_drop_date,
            'start_price': df.loc[df['snapped_at'] == max_drop_date - pd.Timedelta(days=days), 'price'].iloc[0],
            'end_price': df.loc[df['snapped_at'] == max_drop_date, 'price'].iloc[0]
        }

    return results


def print_results(results):
    print("\nMaximum Price Drops Analysis:")
    print("-" * 80)
    for period, data in results.items():
        print(f"\n{period.replace('_', ' ').title()} Period:")
        print(f"Date of maximum drop: {data['date'].strftime('%Y-%m-%d')}")
        print(f"Absolute drop: ${data['max_drop_absolute']:.2f}")
        print(f"Percentage drop: {data['max_drop_percentage']:.2f}%")
        print(f"Price change: ${data['start_price']              :.2f} -> ${data['end_price']:.2f}")


csv_path = "mina-usd-max.csv"
results = calculate_price_drops(csv_path)
print_results(results)
