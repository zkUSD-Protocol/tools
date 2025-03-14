from typing import Dict, Any

# Risk setups
RISK_SETUPS = {
    "low_risk": {
        "health_factor_mean": 220,
        "health_factor_std": 40,
        "min_health_factor": 110,
        "description": "Conservative risk parameters"
    },
    "medium_risk": {
        "health_factor_mean": 180,
        "health_factor_std": 35,
        "min_health_factor": 108,
        "description": "Balanced risk parameters"
    },
    "high_risk": {
        "health_factor_mean": 140,
        "health_factor_std": 25,
        "min_health_factor": 105,
        "description": "Aggressive risk parameters"
    }
}

# Scale setups
SCALE_SETUPS = {
    "low_scale": {
        "num_vaults": 5000,
        "description": "Small protocol scale"
    },
    "medium_scale": {
        "num_vaults": 20000,
        "description": "Medium protocol scale"
    },
    "high_scale": {
        "num_vaults": 50000,
        "description": "Large protocol scale"
    }
}

# Price drop scenarios
PRICE_SCENARIOS = {

    # 1 day scenarios

    "30%_drop_1_day": {
        "start_price": 1,
        "end_price": 0.7,
        "price_drop_duration": 24,  # hours
        "description": "30% drop in 1 day"
    },

    "50%_drop_1_day": {
        "start_price": 1,
        "end_price": 0.5,
        "price_drop_duration": 24,  # hours
        "description": "50% drop in 1 day"
    },

    # 3 day scenarios

    "40%_drop_3_days": {
        "start_price": 1,
        "end_price": 0.6,
        "price_drop_duration": 72,  # hours
        "description": "40% drop in 3 days"
    },

    "60%_drop_3_days": {
        "start_price": 1,
        "end_price": 0.4,
        "price_drop_duration": 72,  # hours
        "description": "60% drop in 3 days"
    },

    # 5 day scenarios

    "45%_drop_5_days": {
        "start_price": 1,
        "end_price": 0.7,
        "price_drop_duration": 120,  # hours
        "description": "30% drop in 5 days"
    },

    "70%_drop_5_days": {
        "start_price": 1,
        "end_price": 0.3,
        "price_drop_duration": 120,  # hours
        "description": "70% drop in 5 days"
    },

    # 7 day scenarios

    "50%_drop_7_days": {
        "start_price": 1,
        "end_price": 0.5,
        "price_drop_duration": 168,  # hours
        "description": "50% drop in 7 days"
    },

    "80%_drop_7_days": {
        "start_price": 1,
        "end_price": 0.2,
        "price_drop_duration": 168,  # hours
        "description": "80% drop in 7 days"
    },

}


def generate_scenario_params(base_params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Generate all combinations of scenarios with different risk and scale setups"""
    scenarios = {}

    for price_scenario_name, price_scenario in PRICE_SCENARIOS.items():
        for risk_setup_name, risk_setup in RISK_SETUPS.items():
            for scale_setup_name, scale_setup in SCALE_SETUPS.items():
                # Create scenario name
                scenario_name = f"{price_scenario_name}_{risk_setup_name}_{scale_setup_name}"

                # Start with base parameters
                scenario_params = base_params.copy()

                # Update parameters for this scenario
                scenario_params.update({
                    # Price scenario parameters
                    'start_price': price_scenario['start_price'],
                    'end_price': price_scenario['end_price'],
                    # convert to hours
                    'price_drop_duration': price_scenario['price_drop_duration'],

                    # Risk setup parameters
                    'min_health_factor': risk_setup['min_health_factor'],
                    'health_factor_mean': risk_setup['health_factor_mean'],
                    'health_factor_std': risk_setup['health_factor_std'],

                    # Scale setup parameters
                    'num_vaults': scale_setup['num_vaults'],

                    # Metadata
                    'scenario_description': (
                        f"{price_scenario['description']} with {risk_setup['description']} "
                        f"at {scale_setup['description']}"
                    )
                })

                scenarios[scenario_name] = scenario_params

    return scenarios
