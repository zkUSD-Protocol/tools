from utils import calculate_health_factor, get_health_status, get_protocol_status
from models.engine import Engine
from config.params import SIMULATION_PARAMS
import numpy as np
import pandas as pd
from datetime import datetime
import os


class Simulation:
    def __init__(self, scenario_params=None, scenario_name="baseline"):
        """
        Initialize simulation with optional scenario parameters

        Args:
            scenario_params (dict): Override parameters for this scenario
            scenario_name (str): Name of the scenario being run
        """
        # Initialize parameters with defaults, then override with scenario params
        self.params = SIMULATION_PARAMS.copy()
        if scenario_params:
            self.params.update(scenario_params)

        # Store scenario information
        self.scenario_name = scenario_name
        self.scenario_description = self.params.get(
            'scenario_description', 'Default scenario')

        # Initialize engine with scenario parameters
        self.engine = Engine(self.params)

        # Setup simulation parameters
        self.start_price = self.params['start_price']
        self.end_price = self.params['end_price']
        self.price_drop_duration = self.params['price_drop_duration']
        self.block_time = self.params['block_time']
        self.txs_per_block = self.params['txs_per_block']

        # Add recovery phase parameters
        self.recovery_duration = self.params.get(
            'recovery_duration', self.price_drop_duration)  # Default to same as drop duration
        # Maximum steps to prevent infinite loops
        self.max_simulation_steps = self.params.get(
            'max_simulation_steps', 1000)

        # Calculate price path
        self.blocks_during_price_drop = int(
            self.price_drop_duration * 60 / self.block_time)
        self.price_path = np.linspace(
            self.start_price, self.end_price, self.blocks_during_price_drop)

        # Initialize results storage
        self.simulation_results = []

    def run_simulation(self, iteration=0, silent=False):
        """Run the simulation and return results and distribution data"""
        # Initialize vaults
        self.engine.create_vaults()

        # Collect initial health factors for reporting
        initial_health_factors = [
            vault.initial_health_factor for vault in self.engine.get_vaults()]

        # Calculate initial metrics
        metrics = self.calculate_protocol_metrics()

        # Store histogram data for distribution DataFrame
        hist, bin_edges = np.histogram(
            initial_health_factors, bins=30, range=(100, 300))

        # Create distribution data dictionary
        distribution_data = {
            'scenario_name': self.scenario_name,
            'scenario_description': self.scenario_description,
            'iteration': iteration,
            'num_vaults': self.params['num_vaults'],
            'health_factor_mean': self.params.get('health_factor_mean', 150),
            'health_factor_std': self.params.get('health_factor_std', 30),
            'min_health_factor': self.params.get('min_health_factor', 105),
            'hf_hist_values': ','.join(map(str, hist.tolist())),
            'hf_hist_bins': ','.join(map(str, bin_edges.tolist())),
            'hf_mean': float(np.mean(initial_health_factors)),
            'hf_median': float(np.median(initial_health_factors)),
            'hf_std': float(np.std(initial_health_factors))
        }

        # Store initial state in main results
        self._store_step_results(0, metrics, iteration, phase="initial")

        if not silent:
            print(
                f"\nScenario: {self.scenario_name} - Iteration: {iteration + 1}")
            print(f"Description: {self.scenario_description}")
            print("\nInitial State:")
            self.print_protocol_status(metrics)

        # Run price drop phase
        for step, price in enumerate(self.price_path, 1):
            self.engine.set_price(price)
            self.engine.check_and_queue_liquidations()

            # Process both liquidations and recoveries during price drop phase
            recoveries_to_process_during_liquidations = 5
            liquidations_this_step = self.engine.max_liquidations_per_step

            if (self.engine.get_recovery_queue_size() > 0 and
                self.engine.get_liquidation_queue_size() > 0 and
                    not self.engine.reserve_fund_depleted):
                self.engine.process_insolvent_vaults_with_reserve_fund(
                    recoveries_to_process_during_liquidations)
                liquidations_this_step -= recoveries_to_process_during_liquidations

            self.engine.process_liquidations(liquidations_this_step)

            metrics = self.calculate_protocol_metrics()
            self._store_step_results(
                step, metrics, iteration, phase="price_drop")

            if not silent and step % 5 == 0:
                print(f"\nStep {step} (Price Drop Phase):")
                self.print_protocol_status(metrics)

        # Run recovery phase until all liquidatable vaults are processed or max steps reached
        recovery_step = 0
        max_recovery_steps = int(self.recovery_duration * 60 / self.block_time)

        while True:
            recovery_step += 1
            total_step = step + recovery_step

            # Check termination conditions
            if recovery_step > max_recovery_steps:
                if not silent:
                    print(
                        f"\nReached maximum recovery duration ({self.recovery_duration} hours)")
                break

            if total_step > self.max_simulation_steps:
                if not silent:
                    print(
                        f"\nReached maximum simulation steps ({self.max_simulation_steps})")
                break

            # Process liquidations at stable price
            liquidations_this_step = self.engine.max_liquidations_per_step
            recoveries_to_process_during_liquidations = 5

            if (self.engine.get_recovery_queue_size() > 0 and
                self.engine.get_liquidation_queue_size() > 0 and
                    not self.engine.reserve_fund_depleted):
                self.engine.process_insolvent_vaults_with_reserve_fund(
                    recoveries_to_process_during_liquidations)
                liquidations_this_step -= recoveries_to_process_during_liquidations

            self.engine.check_and_queue_liquidations()
            self.engine.process_liquidations(liquidations_this_step)

            metrics = self.calculate_protocol_metrics()
            self._store_step_results(
                total_step, metrics, iteration, phase="recovery")

            # Check if all liquidatable vaults have been processed
            if (metrics['num_liquidatable_vaults'] == 0 and
                    self.engine.get_liquidation_queue_size() == 0):

                # Process any remaining insolvent vaults if reserve fund is available
                if (self.engine.get_recovery_queue_size() > 0 and
                        not self.engine.reserve_fund_depleted):
                    self.engine.process_insolvent_vaults_with_reserve_fund(
                        self.engine.max_liquidations_per_step)
                else:
                    if not silent:
                        print(
                            f"\nAll liquidatable vaults processed after {(recovery_step * self.block_time) / 60:.1f} hours of recovery")
                    break

            if not silent and recovery_step % 5 == 0:
                # Calculate hours since price drop ended
                recovery_hours = (recovery_step * self.block_time) / 60
                print(
                    f"\nStep {total_step} (Recovery Phase, {recovery_hours:.1f} hours after drop):")
                self.print_protocol_status(metrics)

        # Print final state
        if not silent:
            print("\nFINAL STATE:")
            self.print_protocol_status(metrics)
            print(f"\nSimulation completed after {total_step} steps")
            print(f"Price drop duration: {self.price_drop_duration} hours")
            print(
                f"Recovery duration: {(recovery_step * self.block_time) / 60:.1f} hours")
            print(
                f"Total simulation time: {(total_step * self.block_time) / 60:.1f} hours")

        return self.simulation_results, distribution_data

    def _store_step_results(self, step, metrics, iteration, phase="price_drop"):
        """Store results for each simulation step"""
        result = {
            'scenario_name': self.scenario_name,
            'scenario_description': self.scenario_description,
            'iteration': iteration,
            'step': step,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'simulation_phase': phase,

            # Price and timing metrics
            'price': metrics['current_price'],
            'price_drop_percentage': ((self.start_price - metrics['current_price']) /
                                      self.start_price * 100),
            'simulation_hour': (step * self.block_time) / 60,

            # Protocol metrics
            'total_collateral': metrics['total_collateral'],
            'total_collateral_value': metrics['total_collateral_value'],
            'total_debt': metrics['total_debt'],
            'protocol_health_factor': metrics['protocol_health_factor'],
            'total_insolvent_collateral': metrics['total_insolvent_collateral'],
            'total_insolvent_collateral_value': metrics['total_insolvent_collateral_value'],
            'total_debt_in_insolvent_vaults': metrics['total_debt_in_insolvent_vaults'],
            # Vault metrics
            'num_healthy_vaults': metrics['num_healthy_vaults'],
            'num_at_risk_vaults': metrics['num_at_risk_vaults'],
            'num_liquidatable_vaults': metrics['num_liquidatable_vaults'],
            'num_liquidated_vaults': metrics['num_liquidated_vaults'],
            'num_insolvent_vaults': metrics['num_insolvent_vaults'],

            # Reserve fund metrics
            'reserve_fund': metrics['reserve_fund'],
            'initial_reserve_fund': metrics['initial_reserve_fund'],
            'reserve_fund_used': metrics['reserve_fund_used'],
            'reserve_fund_percentage': metrics['reserve_fund_percentage'],
            'reserve_fund_used_percentage': metrics['reserve_fund_used_percentage'],

            # Scenario parameters
            'num_vaults': self.params['num_vaults'],
            'price_drop_duration': self.params['price_drop_duration'],
            'collateralisation_ratio': self.params['collateralisation_ratio'],
            'health_factor_mean': self.params['health_factor_mean'],
            'health_factor_std': self.params['health_factor_std'],
            'min_health_factor': self.params['min_health_factor'],
        }

        # Calculate additional metrics
        if metrics['total_debt'] > 0:
            result['collateralization_ratio'] = (
                metrics['total_collateral_value'] / metrics['total_debt'] * 100
            )
        else:
            result['collateralization_ratio'] = float('inf')

        result['liquidation_queue_size'] = self.engine.get_liquidation_queue_size()

        self.simulation_results.append(result)

    def calculate_protocol_metrics(self):
        """Calculate key health metrics for the entire protocol"""
        vaults = self.engine.get_vaults()
        current_price = self.engine.get_price()

        # Initialize counters
        total_collateral = 0
        total_collateral_value = 0
        total_debt = 0
        num_healthy_vaults = 0
        num_at_risk_vaults = 0
        num_liquidatable_vaults = 0
        num_liquidated_vaults = 0
        num_insolvent_vaults = 0
        total_insolvent_collateral = 0
        total_insolvent_collateral_value = 0
        total_debt_in_insolvent_vaults = 0

        # Import thresholds from utils
        from utils import HEALTH_FACTOR_THRESHOLDS

        # Single pass through all vaults
        for vault in vaults:
            # Get basic vault metrics
            collateral_amount = vault.get_collateral_amount()
            collateral_value = vault.get_collateral_value(current_price)
            debt_amount = vault.get_debt_amount()
            health_factor = vault.calculate_health_factor(current_price)

            # Accumulate totals
            total_collateral += collateral_amount
            total_collateral_value += collateral_value
            total_debt += debt_amount

            # Categorize vault
            if collateral_amount == 0:
                num_liquidated_vaults += 1
            elif health_factor < HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']:
                num_insolvent_vaults += 1
                total_insolvent_collateral += collateral_amount
                total_insolvent_collateral_value += collateral_value
                total_debt_in_insolvent_vaults += debt_amount
            elif health_factor >= HEALTH_FACTOR_THRESHOLDS['SAFE'] and health_factor != float('inf'):
                num_healthy_vaults += 1
            elif HEALTH_FACTOR_THRESHOLDS['LIQUIDATION'] <= health_factor < HEALTH_FACTOR_THRESHOLDS['SAFE']:
                num_at_risk_vaults += 1
            elif health_factor < HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']:
                num_liquidatable_vaults += 1

        # Protocol health factor (similar to vault health factor but protocol-wide)
        protocol_health_factor = calculate_health_factor(
            total_collateral, total_debt, current_price)

        # Get reserve fund information
        reserve_fund = self.engine.get_reserve_fund()
        initial_reserve_fund = self.engine.get_initial_reserve_fund()
        reserve_fund_used = self.engine.get_reserve_fund_used()

        return {
            'total_collateral': total_collateral,
            'total_collateral_value': total_collateral_value,
            'total_debt': total_debt,
            'protocol_health_factor': protocol_health_factor,
            'num_healthy_vaults': num_healthy_vaults,
            'num_at_risk_vaults': num_at_risk_vaults,
            'num_liquidatable_vaults': num_liquidatable_vaults,
            'num_liquidated_vaults': num_liquidated_vaults,
            'num_insolvent_vaults': num_insolvent_vaults,
            'total_insolvent_collateral': total_insolvent_collateral,
            'total_insolvent_collateral_value': total_insolvent_collateral_value,
            'total_debt_in_insolvent_vaults': total_debt_in_insolvent_vaults,
            'current_price': current_price,
            'reserve_fund': reserve_fund,
            'initial_reserve_fund': initial_reserve_fund,
            'reserve_fund_used': reserve_fund_used,
            'reserve_fund_percentage': (reserve_fund / initial_reserve_fund * 100) if initial_reserve_fund > 0 else 0,
            'reserve_fund_used_percentage': (reserve_fund_used / initial_reserve_fund * 100) if initial_reserve_fund > 0 else 0
        }

    def print_protocol_status(self, metrics):
        """Print detailed protocol status"""
        print("\n" + "="*100)
        print(f"PROTOCOL STATUS REPORT")
        print("-"*100)
        print(f"Total Collateral: {metrics['total_collateral']:,.0f} MINA")
        print(f"Current Price: ${metrics['current_price']:.3f}")
        print(
            f"Protocol Health Factor: {metrics['protocol_health_factor']:.0f}")
        print(
            f"Status: {get_protocol_status(metrics['protocol_health_factor'], (metrics['num_healthy_vaults'] + metrics['num_at_risk_vaults']))}")
        print(
            f"Total Collateral Value: ${metrics['total_collateral_value']:,.2f}")
        print(f"Total Debt: ${metrics['total_debt']:,.2f}")
        print(
            f"Collateralization Ratio: {(metrics['total_collateral_value']/metrics['total_debt']*100 if metrics['total_debt'] > 0 else float('inf')):.2f}%")
        print(
            f"Total Insolvent Collateral: {metrics['total_insolvent_collateral']:,.0f} MINA")
        print(
            f"Total Insolvent Collateral Value: ${metrics['total_insolvent_collateral_value']:,.2f}")
        print(
            f"Total Debt in Insolvent Vaults: ${metrics['total_debt_in_insolvent_vaults']:,.2f}")
        print(
            f"Initial Reserve Fund: ${metrics['initial_reserve_fund']:,.2f}")
        print(
            f"Reserve Fund: ${metrics['reserve_fund']:,.2f} ({metrics['reserve_fund_percentage']:.2f}%)")
        print(
            f"Reserve Fund Used: ${metrics['reserve_fund_used']:,.2f} ({metrics['reserve_fund_used_percentage']:.2f}%)")
        print("\nVault Distribution:")
        print(f"  Healthy Vaults: {metrics['num_healthy_vaults']} "
              f"({metrics['num_healthy_vaults']/len(self.engine.get_vaults())*100:.1f}%)")
        print(f"  At Risk Vaults: {metrics['num_at_risk_vaults']} "
              f"({metrics['num_at_risk_vaults']/len(self.engine.get_vaults())*100:.1f}%)")
        print(f"  Liquidatable Vaults: {metrics['num_liquidatable_vaults']} "
              f"({metrics['num_liquidatable_vaults']/len(self.engine.get_vaults())*100:.1f}%)")
        print(f"  Insolvent Vaults: {metrics['num_insolvent_vaults']} "
              f"({metrics['num_insolvent_vaults']/len(self.engine.get_vaults())*100:.1f}%)")
        print(f"  Liquidated Vaults: {metrics['num_liquidated_vaults']} "
              f"({metrics['num_liquidated_vaults']/len(self.engine.get_vaults())*100:.1f}%)")

        if metrics['num_liquidatable_vaults'] + metrics['num_insolvent_vaults'] > 0:
            blocks_needed = (metrics['num_liquidatable_vaults'] + metrics['num_insolvent_vaults']) / \
                self.txs_per_block
            time_needed_minutes = (blocks_needed * self.block_time)
            if time_needed_minutes >= 60:
                print(
                    f"Time to liquidate all remaining vaults: {time_needed_minutes/60:.1f} hours")
            else:
                print(
                    f"Time to liquidate all remaining vaults: {time_needed_minutes:.1f} minutes")
        print("="*100)

    def print_vault_snapshot(self):
        """Print a summary of all vaults' state"""
        vaults = self.engine.get_vaults()
        current_price = self.engine.get_price()

        print("\n" + "="*80)
        print(f"{'Vault ID':^10} | {'Collateral':^15} | {'Debt':^15} | {'Health Factor':^15} | {'Status':^10}")
        print("-"*80)

        for idx, vault in enumerate(vaults):
            health_factor = vault.calculate_health_factor(current_price)
            status = vault.get_health_status(current_price)
            print(f"{idx:^10} | "
                  f"{vault.get_collateral_amount():>13,.0f} | "
                  f"${vault.get_collateral_value(current_price):>13,.0f} | "
                  f"${vault.get_debt_amount():>13,.0f} | "
                  f"{health_factor:>13.0f} | "
                  f"{status:^10}")

        print("-"*80)
        total_collateral = sum(v.get_collateral_amount()
                               for v in vaults)
        total_debt = sum(v.get_debt_amount() for v in vaults)
        total_collateral_value = sum(
            v.get_collateral_value(current_price) for v in vaults)
        print(f"{'TOTALS':^10} | {total_collateral:>13,.0f} | "
              f"${total_collateral_value:>13,.0f} | ${total_debt:>13,.0f} |")
        print("="*80)
