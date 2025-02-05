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

        # Calculate price path
        self.blocks_during_price_drop = int(
            self.price_drop_duration * 60 / self.block_time)
        self.price_path = np.linspace(
            self.start_price, self.end_price, self.blocks_during_price_drop)

        # Initialize results storage
        self.simulation_results = []

    def run_simulation(self, iteration=0, silent=True):
        """
        Run a single simulation iteration

        Args:
            iteration (int): Current iteration number
            silent (bool): Whether to suppress status prints
        """
        # Initialize vaults
        self.engine.create_vaults()

        # Collect initial state
        initial_metrics = self.calculate_protocol_metrics()
        self._store_step_results(0, initial_metrics, iteration)

        if not silent:
            print(f"\nScenario: {
                  self.scenario_name} - Iteration: {iteration + 1}")
            print(f"Description: {self.scenario_description}")
            print("\nInitial State:")
            self.print_protocol_status(initial_metrics)

        # Run simulation steps
        for step, price in enumerate(self.price_path, 1):
            self.engine.set_price(price)
            self.engine.check_and_queue_liquidations()
            self.engine.process_liquidations()

            metrics = self.calculate_protocol_metrics()
            self._store_step_results(step, metrics, iteration)

            if not silent and step % 5 == 0:
                print(f"\nStep {step}:")
                self.print_protocol_status(metrics)

        return self.simulation_results

    def _store_step_results(self, step, metrics, iteration):
        """Store results for each simulation step"""
        result = {
            'scenario_name': self.scenario_name,
            'scenario_description': self.scenario_description,
            'iteration': iteration,
            'step': step,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

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

            # Vault metrics
            'num_healthy_vaults': metrics['num_healthy_vaults'],
            'num_at_risk_vaults': metrics['num_at_risk_vaults'],
            'num_liquidatable_vaults': metrics['num_liquidatable_vaults'],
            'num_liquidated_vaults': metrics['num_liquidated_vaults'],

            # Scenario parameters
            'num_vaults': self.params['num_vaults'],
            'price_drop_duration': self.params['price_drop_duration'],
            'collateralisation_ratio': self.params['collateralisation_ratio'],
            'min_health_factor': self.params['min_health_factor'],
            'max_health_factor': self.params['max_health_factor'],
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

        total_collateral = sum(v.get_collateral_amount() for v in vaults)
        total_collateral_value = sum(
            v.get_collateral_value(current_price) for v in vaults)
        total_debt = sum(v.get_debt_amount() for v in vaults)

        # Protocol health factor (similar to vault health factor but protocol-wide)
        protocol_health_factor = calculate_health_factor(
            total_collateral, total_debt, current_price)

        # Calculate some risk metrics
        num_healthy_vaults = sum(
            1 for v in vaults if v.calculate_health_factor(current_price) >= 150 and v.calculate_health_factor(current_price) != float('inf'))
        num_at_risk_vaults = sum(
            1 for v in vaults if 100 <= v.calculate_health_factor(current_price) < 150)
        num_liquidatable_vaults = sum(1 for v in vaults if v.calculate_health_factor(
            current_price) < 100 and v.get_collateral_amount() > 0)
        num_liquidated_vaults = sum(
            1 for v in vaults if v.get_collateral_amount() == 0)

        return {
            'total_collateral': total_collateral,
            'total_collateral_value': total_collateral_value,
            'total_debt': total_debt,
            'protocol_health_factor': protocol_health_factor,
            'num_healthy_vaults': num_healthy_vaults,
            'num_at_risk_vaults': num_at_risk_vaults,
            'num_liquidatable_vaults': num_liquidatable_vaults,
            'num_liquidated_vaults': num_liquidated_vaults,
            'current_price': current_price
        }

    def print_protocol_status(self, metrics):
        """Print detailed protocol status"""
        print("\n" + "="*100)
        print(f"PROTOCOL STATUS REPORT")
        print("-"*100)
        print(f"Total Collateral: {metrics['total_collateral']:,.0f} MINA")
        print(f"Current Price: ${metrics['current_price']:.3f}")
        print(f"Protocol Health Factor: {
              metrics['protocol_health_factor']:.0f}")
        print(f"Status: {get_protocol_status(
            metrics['protocol_health_factor'], (metrics['num_healthy_vaults'] + metrics['num_at_risk_vaults']))}")
        print(f"Total Collateral Value: ${
              metrics['total_collateral_value']:,.2f}")
        print(f"Total Debt: ${metrics['total_debt']:,.2f}")
        print(f"Collateralization Ratio: {
              (metrics['total_collateral_value']/metrics['total_debt']*100 if metrics['total_debt'] > 0 else float('inf')):.2f}%")
        print("\nVault Distribution:")
        print(f"  Healthy Vaults: {metrics['num_healthy_vaults']} "
              f"({metrics['num_healthy_vaults']/len(self.engine.get_vaults())*100:.1f}%)")
        print(f"  At Risk Vaults: {metrics['num_at_risk_vaults']} "
              f"({metrics['num_at_risk_vaults']/len(self.engine.get_vaults())*100:.1f}%)")
        print(f"  Liquidatable Vaults: {metrics['num_liquidatable_vaults']} "
              f"({metrics['num_liquidatable_vaults']/len(self.engine.get_vaults())*100:.1f}%)")
        print(f"  Liquidated Vaults: {metrics['num_liquidated_vaults']} "
              f"({metrics['num_liquidated_vaults']/len(self.engine.get_vaults())*100:.1f}%)")

        if metrics['num_liquidatable_vaults'] > 0:
            blocks_needed = metrics['num_liquidatable_vaults'] / \
                self.txs_per_block
            time_needed_minutes = (blocks_needed * self.block_time)
            if time_needed_minutes >= 60:
                print(f"Time to liquidate all remaining vaults: {
                      time_needed_minutes/60:.1f} hours")
            else:
                print(f"Time to liquidate all remaining vaults: {
                      time_needed_minutes:.1f} minutes")
        print("="*100)

    def print_vault_snapshot(self):
        """Print a summary of all vaults' state"""
        vaults = self.engine.get_vaults()
        current_price = self.engine.get_price()

        print("\n" + "="*80)
        print(f"{'Vault ID':^10} | {'Collateral':^15} | {
            'Debt':^15} | {'Health Factor':^15} | {'Status':^10}")
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
