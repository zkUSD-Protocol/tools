from datetime import datetime
import os
import pandas as pd
from services.simulation import Simulation
from config.scenarios import generate_scenario_params
from config.params import SIMULATION_PARAMS


def run_batch_simulations(scenarios, iterations_per_scenario=5):
    """
    Run multiple scenarios with multiple iterations each

    Args:
        scenarios (dict): Dictionary of scenario names and their parameters
        iterations_per_scenario (int): Number of iterations to run for each scenario

    Returns:
        tuple: (results_df, distributions_df, results_path)
    """
    all_results = []
    all_distributions = []

    print(
        f"Running {len(scenarios)} scenarios with {iterations_per_scenario} iterations each")

    for scenario_name, scenario_params in scenarios.items():
        print(f"\nRunning scenario: {scenario_name}")

        for i in range(iterations_per_scenario):
            sim = Simulation(scenario_params, scenario_name)
            results, distribution_data = sim.run_simulation(
                iteration=i, silent=True)

            all_results.extend(results)
            all_distributions.append(distribution_data)

            # Print progress
            print(
                f"  Completed iteration {i+1}/{iterations_per_scenario}", end="\r")

        print(f"  Completed all iterations for {scenario_name}           ")

    # Convert results to DataFrames
    results_df = pd.DataFrame(all_results)
    distributions_df = pd.DataFrame(all_distributions)

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_path = f'results/simulation_results_{timestamp}.csv'
    distributions_path = f'results/health_distributions_{timestamp}.csv'

    # Create directory if it doesn't exist
    os.makedirs('results', exist_ok=True)

    # Save to CSV
    results_df.to_csv(results_path, index=False)
    distributions_df.to_csv(distributions_path, index=False)

    print(f"\nResults saved to {results_path}")
    print(f"Health factor distributions saved to {distributions_path}")

    return results_df, distributions_df, results_path


def main():
    # Generate all scenario combinations
    scenarios = generate_scenario_params(SIMULATION_PARAMS)

    # Print scenario overview
    print("Running the following scenarios:")
    for name, params in scenarios.items():
        print(f"\n{name}:")
        print(f"  Description: {params['scenario_description']}")
        print(f"  Vaults: {params['num_vaults']}")
        print(
            f"  Health Factor Range: {params['min_health_factor']}-{params['max_health_factor']}")
        print(f"  Price Drop: {params['start_price']} -> {params['end_price']} "
              f"over {params['price_drop_duration']} hours")

    # Run all scenarios
    results_df, distributions_df, results_path = run_batch_simulations(
        scenarios, iterations_per_scenario=1)

    print("\nSimulation batch complete!")
    print(f"Total scenarios run: {len(scenarios)}")
    print(f"Total rows of data: {len(results_df)}")

    # Basic statistics
    print("\nScenario Summary:")
    summary = results_df.groupby('scenario_name').agg({
        'protocol_health_factor': ['mean', 'min', 'max'],
        'num_liquidated_vaults': ['mean', 'max'],
    }).round(2)
    print(summary)


if __name__ == "__main__":
    main()
