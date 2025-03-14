import argparse
from pathlib import Path
from datetime import datetime
import re
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
        print(
            f"  Mean Health Factor: {params['health_factor_mean']} with std {params['health_factor_std']}")
        print(f"  Price Drop: {params['start_price']} -> {params['end_price']} "
              f"over {params['price_drop_duration']} hours")

    # Run all scenarios
    results_df, distributions_df, results_path = run_batch_simulations(
        scenarios, iterations_per_scenario=1)

    print("\nScenario simulations complete!")
    print(f"Total scenarios run: {len(scenarios)}")
    print(f"Total rows of data: {len(results_df)}")


def analyze_results(results_file=None, distributions_file=None):
    """Analyze simulation results and generate reports"""
    results_dir = Path('results')

    # If no results file specified, find the most recent one
    if results_file is None:
        results_files = list(results_dir.glob('simulation_results_*.csv'))
        if not results_files:
            print("No results files found!")
            return
        results_file = max(results_files, key=lambda x: x.stat().st_mtime)
    else:
        results_file = Path(results_file)

    # If no distributions file specified, try to find the matching one
    if distributions_file is None:
        # Extract timestamp from results filename
        timestamp_match = re.search(r'(\d{8}_\d{6})', results_file.name)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            potential_dist_file = results_dir / \
                f'health_distributions_{timestamp}.csv'
            if potential_dist_file.exists():
                distributions_file = potential_dist_file
            else:
                # Try to find any distributions file with similar timestamp
                dist_files = list(results_dir.glob(
                    'health_distributions_*.csv'))
                if dist_files:
                    # Find the closest match by modification time
                    results_mtime = results_file.stat().st_mtime
                    distributions_file = min(dist_files,
                                             key=lambda x: abs(x.stat().st_mtime - results_mtime))
                    print(
                        f"Using closest matching distributions file: {distributions_file}")
                else:
                    print(
                        "No health distributions file found. Will use synthetic data.")
        else:
            # If no timestamp in filename, try to find any distributions file
            dist_files = list(results_dir.glob('health_distributions_*.csv'))
            if dist_files:
                distributions_file = max(
                    dist_files, key=lambda x: x.stat().st_mtime)
                print(
                    f"Using most recent distributions file: {distributions_file}")
            else:
                print("No health distributions file found. Will use synthetic data.")
    else:
        distributions_file = Path(distributions_file)

    print(f"Analyzing results from: {results_file}")
    if distributions_file:
        print(f"Using health factor distributions from: {distributions_file}")

    # Generate report
    report = ReportGenerator(results_file, distributions_file)
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

    parser.add_argument(
        '--distributions-file',
        type=str,
        help='Specific health factor distributions file to use (for analyze command)'
    )

    args = parser.parse_args()

    if args.command == 'simulate':
        run_single_simulation()
    elif args.command == 'scenarios':
        run_scenarios()
    elif args.command == 'analyze':
        analyze_results(args.results_file, args.distributions_file)


if __name__ == "__main__":
    main()
