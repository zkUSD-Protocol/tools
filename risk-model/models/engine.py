from collections import deque
import numpy as np
from .vault import Vault
from config.params import SIMULATION_PARAMS
from utils import HEALTH_FACTOR_THRESHOLDS


class Engine:
    def __init__(self, params=None):
        """Initialize the engine with optional scenario parameters"""
        self.params = SIMULATION_PARAMS.copy()
        if params:
            self.params.update(params)

        self.vaults = []
        self.current_price = self.params['start_price']
        self.liquidation_queue = deque()
        self.recovery_queue = deque()
        self.max_liquidations_per_step = self.params['txs_per_block']

        # Initialize reserve fund to zero - will be set after vaults are created
        self.reserve_fund = 0
        self.initial_reserve_fund = 0
        self.reserve_fund_used = 0

        self.reserve_fund_depleted = False

    def create_vaults(self):
        """Create vaults and initialize the reserve fund"""
        self.vaults = [Vault(self.params)
                       for _ in range(self.params['num_vaults'])]

        # Calculate total debt in the system
        total_debt = sum(vault.get_debt_amount() for vault in self.vaults)

        print(f"Total debt: {total_debt}")

        # Set reserve fund to configured percentage of total debt
        self.reserve_fund = total_debt * \
            self.params['reserve_fund_percentage_of_debt']
        self.initial_reserve_fund = self.reserve_fund
        self.reserve_fund_used = 0
        self.reserve_fund_depleted = False

    def get_vaults(self):
        return self.vaults

    def set_price(self, price):
        self.current_price = price

    def get_price(self):
        return self.current_price

    def get_reserve_fund(self):
        return self.reserve_fund

    def get_initial_reserve_fund(self):
        return self.initial_reserve_fund

    def get_reserve_fund_used(self):
        return self.reserve_fund_used

    def process_liquidations(self, liquidations_to_process):
        """Process liquidations from the queue up to the specified limit"""
        liquidations_this_step = 0
        liquidated_vaults = []

        while self.liquidation_queue and liquidations_this_step < liquidations_to_process:
            vault = self.liquidation_queue.popleft()

            # Check if vault is insolvent before liquidating
            health_factor = vault.calculate_health_factor(self.current_price)
            if health_factor < HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']:
                # Move to recovery queue if insolvent
                self.recovery_queue.append(vault)
                continue

            # Liquidate the vault
            vault.liquidate_vault(self.current_price)
            liquidations_this_step += 1
            liquidated_vaults.append(vault)

        return liquidated_vaults

    def check_and_queue_liquidations(self):
        """Check all vaults and queue those that need liquidation"""
        newly_queued = 0
        already_queued = set(self.liquidation_queue)
        already_in_recovery = set(self.recovery_queue)

        for vault in self.vaults:
            # Skip if vault is already in a queue or has no collateral
            if (vault in already_queued or
                vault in already_in_recovery or
                    vault.get_collateral_amount() <= 0):
                continue

            health_factor = vault.calculate_health_factor(self.current_price)

            # Check if vault needs liquidation
            if health_factor < self.params['health_factor_liquidation_threshold']:
                # Check if vault is insolvent and should go to recovery queue
                if health_factor < HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']:
                    self.recovery_queue.append(vault)
                else:
                    self.liquidation_queue.append(vault)
                newly_queued += 1

        return newly_queued

    def process_insolvent_vaults_with_reserve_fund(self, recoveries_to_process):
        """Process insolvent vaults using the reserve fund"""
        recoveries_this_step = 0
        vaults_recovered = []

        while self.recovery_queue and recoveries_this_step < recoveries_to_process:
            vault = self.recovery_queue.popleft()
            debt_amount = vault.get_debt_amount()

            # Skip if vault has no debt
            if debt_amount <= 0:
                continue

            # Check if reserve fund has enough to cover the debt
            if self.reserve_fund >= debt_amount:
                # Calculate collateral value before liquidation
                collateral_amount = vault.get_collateral_amount()
                collateral_value = collateral_amount * self.current_price

                # Use reserve fund to cover debt
                self.reserve_fund -= debt_amount
                self.reserve_fund_used += debt_amount

                # Liquidate the vault
                vault.liquidate_vault(self.current_price)

                # Add collateral value back to reserve fund
                self.reserve_fund += collateral_value

                recoveries_this_step += 1
                vaults_recovered.append(vault)
            else:
                # Put vault back in queue and mark reserve fund as depleted
                self.recovery_queue.appendleft(vault)
                self.reserve_fund_depleted = True
                break

        return vaults_recovered

    def get_liquidation_queue_size(self):
        return len(self.liquidation_queue)

    def get_recovery_queue_size(self):
        return len(self.recovery_queue)
