SIMULATION_PARAMS = {
    # Total number of vaults in the simulation
    'num_vaults': 10000,

    # The average of initial collateral amounts for each vault
    "mean_collateral_amount": 50000,

    # The range of initial health factors for each vault
    "min_health_factor": 110,
    "max_health_factor": 250,

    # Chain parameters
    'block_time': 5,
    'txs_per_block': 24,

    # Simulation parameters
    'start_price': 1,  # in USD
    'end_price': 0.2,  # in USD
    'price_drop_duration': 48,  # in hours

    # Liquidation parameters
    'collateralisation_ratio': 150,  # Percentage
    'health_factor_liquidation_threshold': 100,  # health factor
}
