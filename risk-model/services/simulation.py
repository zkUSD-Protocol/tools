from utils import calculate_health_factor, get_health_status, get_protocol_status
from models.    engine import Engine
from config import SIMULATION_PARAMS
import numpy as np


class Simulation:
    def __init__(self):
        self.engine = Engine()
        self.end_price = SIMULATION_PARAMS['end_price']
        self.price_drop_duration = SIMULATION_PARAMS['price_drop_duration']
        self.block_time = SIMULATION_PARAMS['block_time']
        self.txs_per_block = SIMULATION_PARAMS['txs_per_block']

        # Calculate a price path from start_price to end_price over the specified duration
        self.blocks_during_price_drop = int(
            self.price_drop_duration * 60 / self.block_time)
        self.price_path = np.linspace(
            self.engine.get_price(), self.end_price, self.blocks_during_price_drop)

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
            1 for v in vaults if v.calculate_health_factor(current_price) >= 150)
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
            metrics['protocol_health_factor'])}")
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

    def run(self):
        # Initialize vaults
        self.engine.create_vaults()

        # Print initial state
        print("\nInitial State:")
        initial_metrics = self.calculate_protocol_metrics()
        self.print_protocol_status(initial_metrics)
        self.print_vault_snapshot()

        # Simulate price changes
        for step, price in enumerate(self.price_path):
            self.engine.set_price(price)

            # Check and process liquidations
            self.engine.check_and_queue_liquidations()
            self.engine.process_liquidations()

            if step % 5 == 0:  # Print status every 5 steps
                metrics = self.calculate_protocol_metrics()
                print(f"\nStep {step}:")
                self.print_protocol_status(metrics)
