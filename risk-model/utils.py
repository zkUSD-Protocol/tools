from config.params import SIMULATION_PARAMS


def calculate_health_factor(collateral_amount, debt_amount, price):
    """Calculate health factor for a given collateral and debt amount"""
    if debt_amount == 0:
        return float('inf')
    collateral_value = collateral_amount * price
    max_allowed_debt = calculate_max_allowed_debt(collateral_value)
    return (max_allowed_debt / debt_amount) * 100


def calculate_max_allowed_debt(collateral_value):
    """Calculate maximum allowed debt for a given collateral value"""
    return collateral_value / SIMULATION_PARAMS['collateralisation_ratio'] * 100


def get_health_status(health_factor, is_liquidated=False):
    """Determine status based on health factor"""
    if is_liquidated:
        return "LIQUIDATED"
    elif health_factor >= 200:
        return "VERY HEALTHY"
    elif health_factor >= 150:
        return "HEALTHY"
    elif health_factor >= 120:
        return "CAUTION"
    elif health_factor >= 100:
        return "HIGH RISK"
    else:
        return "LIQUIDATABLE"


def get_protocol_status(health_factor, open_vaults):
    """Determine protocol-wide status based on health factor"""

    if open_vaults == 0:
        return "SUCCESSFULLY LIQUIDATED POSITIONS"

    if health_factor >= 200:
        return "VERY HEALTHY"
    elif health_factor >= 150:
        return "HEALTHY"
    elif health_factor >= 120:
        return "CAUTION"
    elif health_factor >= 100:
        return "HIGH RISK"
    elif health_factor >= 66:
        return "IMMINENT INSOLVENCY"
    else:
        return "INSOLVENT"


def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"


def format_percentage(value):
    """Format value as percentage"""
    return f"{value:.2f}%"
