# zkUSD Risk Model Simulation Tool

A comprehensive simulation tool for testing the zkUSD protocol's resilience under various market conditions and risk parameters.

## Overview

The risk model simulates the behavior of the zkUSD protocol during price drops of varying severity and duration. It models:

- Vault creation with realistic distributions of collateral and health factors
- Price drops based on historical benchmark scenarios and stress tests
- Liquidation processes and their impact on protocol health
- Reserve fund usage for handling insolvent vaults
- Recovery phase after price stabilization

## Features

- **Scenario-based testing**: Run predefined scenarios or create custom ones
- **Multi-scale simulations**: Test with different numbers of vaults (5K, 20K, 50K)
- **Risk parameter testing**: Evaluate different risk configurations (conservative, balanced, aggressive)
- **Comprehensive reporting**: Generate visual reports with heatmaps and charts
- **Historical data integration**: Scenarios based on actual MINA price movements
- **Phase analysis**: Compare protocol health at the end of price drop vs. after recovery

## Installation

### Prerequisites

- Python 3.8+
- Required packages: numpy, pandas, matplotlib, scipy

### Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Running a Single Simulation

To run a single simulation with default parameters:

```
python main.py simulate
```

This will run a simulation using the parameters defined in `config/params.py`.

### Running Multiple Scenarios

To run all predefined scenarios:

```
python main.py scenarios
```

This executes all scenario combinations defined in `config/scenarios.py`, testing different:

- Price drop magnitudes and durations
- Risk parameter configurations
- Protocol scales (number of vaults)

### Analyzing Results

To analyze the most recent simulation results and generate reports:

```
python main.py analyze
```

To analyze specific result files:

```
python main.py analyze --results-file results/simulation_results_20230101_120000.csv --distributions-file results/health_distributions_20230101_120000.csv
```

## Configuration

### Main Configuration Files

- `config/params.py`: Default simulation parameters
- `config/scenarios.py`: Predefined scenarios for batch testing

### Key Parameters

#### Price Scenarios

- Different magnitudes of price drops (30% to 80%)
- Various durations (1 day to 7 days)

#### Risk Setups

- **Conservative**: Higher health factors, lower risk
- **Balanced**: Moderate health factors and risk
- **Aggressive**: Lower health factors, higher risk

#### Initial Scale Setups

- **Small**: 5,000 vaults
- **Medium**: 20,000 vaults
- **Large**: 50,000 vaults

#### Liquidation Parameters

- Collateralization ratio
- Health factor thresholds
- Liquidation speed (transactions per block)

#### Reserve Fund Parameters

- Size relative to total debt
- Usage rules for insolvent vaults

## Simulation Process

The simulation runs in two distinct phases:

1. **Price Drop Phase**:

   - Price decreases according to the scenario parameters
   - Vaults are checked for liquidation eligibility
   - Liquidations and reserve fund usage are processed

2. **Recovery Phase**:
   - Price remains at the final drop level
   - Remaining liquidatable vaults are processed
   - Protocol stabilization is monitored

## Output

The simulation generates:

1. **CSV Data Files**:

   - `simulation_results_[timestamp].csv`: Detailed metrics for each step
   - `health_distributions_[timestamp].csv`: Initial health factor distributions

2. **Visual Reports**:

   - Protocol health factor heatmaps at the end of price drop phase
   - Protocol health factor heatmaps at the end of recovery phase
   - Liquidated vaults percentage heatmaps at the end of price drop phase
   - Liquidated vaults percentage heatmaps at the end of recovery phase
   - Time series charts of key metrics
   - Health factor distribution histograms

3. **Executive Summary**:

   - Markdown report with key findings for all scenarios
   - Health factor category explanations
   - Scenario parameters summary
   - Final state metrics for each scenario
   - Vault distribution breakdown by health status

4. **Step-by-Step Breakdown**:
   - Detailed text report for each scenario
   - Initial parameters and state
   - Separate reporting for price drop and recovery phases
   - Final state analysis
   - Simulation duration statistics

## Project Structure

- `config/`: Configuration files for simulation parameters and scenarios
- `models/`: Core simulation models
  - `engine.py`: Main simulation engine
  - `vault.py`: Vault model with health factor calculations
- `services/`: Simulation services
  - `simulation.py`: Manages the simulation process
- `report/`: Report generation
  - `report_generator.py`: Creates visual reports from simulation data
- `results/`: Output data and reports
- `utils.py`: Utility functions and constants
- `main.py`: Command-line interface
- `run_scenarios.py`: Batch scenario execution

## Interpreting Results

- **Protocol Health Factor**: Higher is better. Values below 100 indicate the protocol is undercollateralized.
- **Liquidated Vaults Percentage**: Lower is better. High percentages may indicate excessive liquidations.
- **Reserve Fund Usage**: Indicates how much of the reserve fund was needed to cover insolvent vaults.
- **Phase Comparison**: Differences between price drop end and recovery end indicate the protocol's ability to stabilize.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
