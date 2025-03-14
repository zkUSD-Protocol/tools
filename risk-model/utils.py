from config.params import SIMULATION_PARAMS

# Health factor thresholds
HEALTH_FACTOR_THRESHOLDS = {
    'INSOLVENCY': 66,      # Below this is insolvent
    'LIQUIDATION': 100,    # Below this is liquidatable
    'SAFE': 150            # Below this is at risk, above is healthy
}


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


def get_health_status(health_factor):
    """
    Get the health status of a vault based on its health factor

    Args:
        health_factor (float): The health factor of the vault

    Returns:
        str: The health status of the vault
    """
    if health_factor == 0:
        return "LIQUIDATED"
    elif health_factor < HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']:
        return "INSOLVENT"
    elif health_factor < HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']:
        return "LIQUIDATABLE"
    elif health_factor < HEALTH_FACTOR_THRESHOLDS['SAFE']:
        return "AT_RISK"
    else:
        return "HEALTHY"


def get_health_status_label(health_factor):
    """
    Get a human-readable health status label with threshold information

    Args:
        health_factor (float): The health factor of the vault

    Returns:
        str: The health status label with threshold information
    """
    if health_factor == 0:
        return "Liquidated"
    elif health_factor < HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']:
        return f"Insolvent (HF < {HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']})"
    elif health_factor < HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']:
        return f"Liquidatable ({HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']} ≤ HF < {HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']})"
    elif health_factor < HEALTH_FACTOR_THRESHOLDS['SAFE']:
        return f"At Risk ({HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']} ≤ HF < {HEALTH_FACTOR_THRESHOLDS['SAFE']})"
    else:
        return f"Healthy (HF ≥ {HEALTH_FACTOR_THRESHOLDS['SAFE']})"


def get_health_status_labels():
    """
    Get all health status labels with threshold information

    Returns:
        dict: A dictionary of health status labels with threshold information
    """
    return {
        'HEALTHY': f"Healthy (HF ≥ {HEALTH_FACTOR_THRESHOLDS['SAFE']})",
        'AT_RISK': f"At Risk ({HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']} ≤ HF < {HEALTH_FACTOR_THRESHOLDS['SAFE']})",
        'LIQUIDATABLE': f"Liquidatable ({HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']} ≤ HF < {HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']})",
        'INSOLVENT': f"Insolvent (HF < {HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']})",
        'LIQUIDATED': "Liquidated"
    }


def get_protocol_status(protocol_health_factor, num_active_vaults):
    """
    Get the overall status of the protocol

    Args:
        protocol_health_factor (float): The health factor of the protocol
        num_active_vaults (int): The number of active vaults

    Returns:
        str: The status of the protocol
    """
    if num_active_vaults == 0:
        return "All vaults liquidated"
    elif protocol_health_factor < HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']:
        return "CRITICAL - Protocol insolvent"
    elif protocol_health_factor < HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']:
        return "SEVERE - Protocol below overcollateralisation ratio"
    elif protocol_health_factor < HEALTH_FACTOR_THRESHOLDS['SAFE']:
        return "WARNING - Protocol at risk"
    else:
        return "HEALTHY - Protocol stable"


def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"


def format_percentage(value):
    """Format value as percentage"""
    return f"{value:.2f}%"
