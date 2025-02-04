from collections import deque
import numpy as np
from .vault import Vault
from config import SIMULATION_PARAMS


class Engine:
    def __init__(self):
        self.vaults = []
        self.current_price = SIMULATION_PARAMS['start_price']
        self.liquidation_queue = deque()  # Queue for vaults pending liquidation
        self.max_liquidations_per_step = SIMULATION_PARAMS['txs_per_block']

    def create_vaults(self):
        self.vaults = [Vault() for _ in range(SIMULATION_PARAMS['num_vaults'])]

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
        for vault in self.vaults:
            if (vault.calculate_health_factor(self.current_price) <
                SIMULATION_PARAMS['health_factor_liquidation_threshold'] and
                    vault.get_collateral_amount() > 0):  # Only queue if not already liquidated
                self.liquidation_queue.append(vault)
                newly_queued += 1
        return newly_queued

    def get_liquidation_queue_size(self):
        return len(self.liquidation_queue)
