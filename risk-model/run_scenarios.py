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
        iterations_per_scenario (int): Number of iterations to run per scenario
    """
    all_results = []

    for scenario_name, scenario_params in scenarios.items():
        print(f"\nRunning scenario: {scenario_name}")
        print(f"Description: {scenario_params.get(
            'scenario_description', '')}")

        for iteration in range(iterations_per_scenario):
            print(f"  Iteration {iteration + 1}/{iterations_per_scenario}")

            # Create and run simulation with scenario parameters
            sim = Simulation(scenario_params, scenario_name)
            results = sim.run_simulation(iteration, silent=True)
            all_results.extend(results)

    # Convert results to DataFrame
    df = pd.DataFrame(all_results)

    # Create 'results' directory if it doesn't exist
    os.makedirs('results', exist_ok=True)

    # Save results with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = f'results/simulation_results_{timestamp}.csv'
    df.to_csv(csv_path, index=False)
    print(f"\nResults saved to: {csv_path}")

    return df


def main():
    # Generate all scenario combinations
    scenarios = generate_scenario_params(SIMULATION_PARAMS)

    # Print scenario overview
    print("Running the following scenarios:")
    for name, params in scenarios.items():
        print(f"\n{name}:")
        print(f"  Description: {params['scenario_description']}")
        print(f"  Vaults: {params['num_vaults']}")
        print(f"  Health Factor Range: {
              params['min_health_factor']}-{params['max_health_factor']}")
        print(f"  Price Drop: {params['start_price']} -> {params['end_price']} "
              f"over {params['price_drop_duration']} hours")

    # Run all scenarios
    results_df = run_batch_simulations(scenarios, iterations_per_scenario=1)

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
