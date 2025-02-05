import argparse
from pathlib import Path
from services.simulation import Simulation
from config.scenarios import generate_scenario_params
from config.params import SIMULATION_PARAMS
from report.report_generator import ReportGenerator
from run_scenarios import run_batch_simulations


def run_single_simulation():
    """Run a single simulation with default parameters"""
    print("Starting single simulation...")
    sim = Simulation()
    sim.run_simulation(silent=False)
    print("\nSimulation Complete!")


def run_scenarios():
    """Run multiple scenarios based on configuration"""
    print("Starting scenario simulations...")

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

    print("\nScenario simulations complete!")
    print(f"Total scenarios run: {len(scenarios)}")
    print(f"Total rows of data: {len(results_df)}")


def analyze_results(results_file=None):
    """Analyze simulation results and generate reports"""
    if results_file is None:
        # Get most recent results file
        results_dir = Path('results')
        results_files = list(results_dir.glob('simulation_results_*.csv'))
        if not results_files:
            print("No results files found!")
            return
        results_file = max(results_files, key=lambda x: x.stat().st_mtime)

    print(f"Analyzing results from: {results_file}")

    # Generate report
    report = ReportGenerator(results_file)
    report.generate_full_report()


def main():
    parser = argparse.ArgumentParser(
        description='Risk Model Simulation Tool',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'command',
        choices=['simulate', 'scenarios', 'analyze'],
        help='''Command to execute:
simulate  - Run a single simulation with default parameters
scenarios - Run multiple scenario simulations
analyze   - Analyze results and generate reports'''
    )

    parser.add_argument(
        '--results-file',
        type=str,
        help='Specific results file to analyze (for analyze command)'
    )

    args = parser.parse_args()

    if args.command == 'simulate':
        run_single_simulation()
    elif args.command == 'scenarios':
        run_scenarios()
    elif args.command == 'analyze':
        analyze_results(args.results_file)


if __name__ == "__main__":
    main()
