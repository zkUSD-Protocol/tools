from config.params import SIMULATION_PARAMS
from utils import calculate_health_factor, calculate_max_allowed_debt, get_health_status
import numpy as np
from scipy import stats


class Vault:
    def __init__(self, params=None):
        """Initialize the vault with optional scenario parameters"""
        self.params = SIMULATION_PARAMS.copy()
        if params:
            self.params.update(params)

        # Generate random collateral amount using normal distribution
        self.collateral_amount = max(1000, round(np.random.normal(
            loc=self.params['mean_collateral_amount'],
            scale=self.params['mean_collateral_amount'] * 1
        )))

        # Get health factor distribution parameters
        mean_hf = self.params.get('health_factor_mean', 150)
        std_hf = self.params.get('health_factor_std', 30)
        # Absolute minimum (safety)
        min_hf = self.params.get('min_health_factor', 105)

        # Use log-normal distribution for right-skewed health factors
        # Convert normal mean/std to log-normal parameters
        # For log-normal: median = exp(mu)
        # We'll set the median of our log-normal to our desired mean
        phi = std_hf / mean_hf  # Coefficient of variation
        sigma = np.sqrt(np.log(1 + phi**2))
        mu = np.log(mean_hf) - 0.5 * sigma**2

        # Generate health factor using log-normal distribution
        # This creates a right-skewed distribution with the specified mean
        self.initial_health_factor = max(
            min_hf, stats.lognorm.rvs(s=sigma, scale=np.exp(mu)))

        # Calculate debt amount based on health factor and starting price
        self.debt_amount = self.calculate_initial_debt_amount()

    def get_collateral_amount(self):
        return self.collateral_amount

    def get_collateral_value(self, price):
        return self.collateral_amount * price

    def get_debt_amount(self):
        return self.debt_amount

    def calculate_initial_debt_amount(self):
        price = self.params['start_price']
        max_allowed_debt = calculate_max_allowed_debt(
            self.collateral_amount * price)
        return max_allowed_debt / (self.initial_health_factor / 100)

    def calculate_health_factor(self, price):
        return calculate_health_factor(self.collateral_amount, self.debt_amount, price)

    def get_health_status(self, price):
        health_factor = self.calculate_health_factor(price)
        is_liquidated = self.collateral_amount == 0
        return get_health_status(health_factor, is_liquidated)

    def liquidate_vault(self, price):
        health_factor = self.calculate_health_factor(price)

        if health_factor < SIMULATION_PARAMS['health_factor_liquidation_threshold']:
            # Calculate liquidation amount
            self.debt_amount = 0
            self.collateral_amount = 0
            return True

        return False
