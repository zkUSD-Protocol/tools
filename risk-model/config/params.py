SIMULATION_PARAMS = {
    # Total number of vaults in the simulation
    'num_vaults': 50000,

    # The average of initial collateral amounts for each vault
    "mean_collateral_amount": 25000,

    # The range of initial health factors for each vault
    "health_factor_mean": 180,
    "health_factor_std": 35,
    "min_health_factor": 105,

    # Chain parameters
    'block_time': 3,  # in minutes
    'txs_per_block': 18,  # transactions

    # Simulation parameters
    'start_price': 1,  # in USD
    'end_price': 0.7,  # in USD
    'price_drop_duration': 24,  # in hours

    # Recovery phase parameters
    'recovery_duration': 480,  # in hours (how long to run recovery phase)
    'max_simulation_steps': 10000,  # maximum steps to prevent infinite loops

    # Liquidation parameters
    'collateralisation_ratio': 150,  # Percentage
    'health_factor_liquidation_threshold': 100,  # health factor

    # Reserve fund parameters
    'reserve_fund_percentage_of_debt': 0.10,
}


"""
Historical Mina Maximum Price Drops Analysis:
----------------------------------

1 Day Period:
Date of maximum drop: 2021-09-21
Absolute drop: $0.91
Percentage drop: 30.55%
Price change: $5.39 -> $4.48

2 Day Period:
Date of maximum drop: 2021-09-22
Absolute drop: $1.23
Percentage drop: 32.85%
Price change: $5.39 -> $4.17

3 Day Period:
Date of maximum drop: 2021-09-22
Absolute drop: $1.13
Percentage drop: 39.70%
Price change: $5.30 -> $4.17

4 Day Period:
Date of maximum drop: 2021-06-08
Absolute drop: $1.32
Percentage drop: 42.80%
Price change: $4.55 -> $3.23

5 Day Period:
Date of maximum drop: 2021-09-21
Absolute drop: $1.58
Percentage drop: 46.19%
Price change: $6.06 -> $4.48

6 Day Period:
Date of maximum drop: 2021-09-22
Absolute drop: $1.89
Percentage drop: 47.97%
Price change: $6.06 -> $4.17

7 Day Period:
Date of maximum drop: 2021-09-22
Absolute drop: $1.99
Percentage drop: 50.94%
Price change: $6.15 -> $4.17
"""
