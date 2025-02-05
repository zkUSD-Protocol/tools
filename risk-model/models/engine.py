from collections import deque
import numpy as np
from .vault import Vault
from config.params import SIMULATION_PARAMS


class Engine:
    def __init__(self, params=None):
        """Initialize the engine with optional scenario parameters"""
        self.params = SIMULATION_PARAMS.copy()
        if params:
            self.params.update(params)

        self.vaults = []
        self.current_price = self.params['start_price']
        self.liquidation_queue = deque()
        self.max_liquidations_per_step = self.params['txs_per_block']

    def create_vaults(self):
        self.vaults = [Vault(self.params)
                       for _ in range(self.params['num_vaults'])]

    def get_vaults(self):
        return self.vaults

    def set_price(self, price):
        self.current_price = price

    def get_price(self):
        return self.current_price

    def process_liquidations(self):
        # Process the max liquidations from the queue
        liquidations_this_step = 0
        liquidated_vaults = []

        while self.liquidation_queue and liquidations_this_step < self.max_liquidations_per_step:
            vault: Vault = self.liquidation_queue.popleft()
            vault.liquidate_vault(self.current_price)
            liquidations_this_step += 1
            liquidated_vaults.append(vault)

        return liquidated_vaults

    def check_and_queue_liquidations(self):
        # Check all vaults and queue those that need liquidation
        newly_queued = 0
        already_queued = set(self.liquidation_queue)

        for vault in self.vaults:
            # Only queue if:
            # 1. Vault is not already in queue
            # 2. Vault has collateral remaining
            # 3. Vault's health factor is below liquidation threshold
            if (vault not in already_queued and
                vault.get_collateral_amount() > 0 and
                vault.calculate_health_factor(self.current_price) <
                    self.params['health_factor_liquidation_threshold']):

                self.liquidation_queue.append(vault)
                newly_queued += 1
        return newly_queued

    def get_liquidation_queue_size(self):
        return len(self.liquidation_queue)
