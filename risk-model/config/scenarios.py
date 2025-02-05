from typing import Dict, Any

# Risk setups
RISK_SETUPS = {
    "low_risk": {
        "min_health_factor": 130,
        "max_health_factor": 300,
        "description": "Conservative risk parameters"
    },
    "medium_risk": {
        "min_health_factor": 120,
        "max_health_factor": 250,
        "description": "Balanced risk parameters"
    },
    "high_risk": {
        "min_health_factor": 110,
        "max_health_factor": 200,
        "description": "Aggressive risk parameters"
    }
}

# Scale setups
SCALE_SETUPS = {
    "low_scale": {
        "num_vaults": 1000,
        "description": "Small protocol scale"
    },
    "medium_scale": {
        "num_vaults": 5000,
        "description": "Medium protocol scale"
    },
    "high_scale": {
        "num_vaults": 10000,
        "description": "Large protocol scale"
    }
}

# Price drop scenarios
PRICE_SCENARIOS = {
    "20%_drop": {
        "start_price": 1,
        "end_price": 0.8,
        "price_drop_duration": 24,  # hours
        "description": "20% drop in 1 day"
    },
    "30%_drop": {
        "start_price": 1,
        "end_price": 0.7,
        "price_drop_duration": 24,  # hours
        "description": "30% drop in 1 day"
    },
    "40%_drop": {
        "start_price": 1,
        "end_price": 0.6,
        "price_drop_duration": 24,  # hours
        "description": "40% drop in 1 day"
    },
    "60%_drop": {
        "start_price": 1,
        "end_price": 0.4,
        "price_drop_duration": 24,  # hours
        "description": "60% drop in 1 day"
    }
}


def generate_scenario_params(base_params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Generate all combinations of scenarios with different risk and scale setups"""
    scenarios = {}

    for price_scenario_name, price_scenario in PRICE_SCENARIOS.items():
        for risk_setup_name, risk_setup in RISK_SETUPS.items():
            for scale_setup_name, scale_setup in SCALE_SETUPS.items():
                # Create scenario name
                scenario_name = f"{price_scenario_name}_{
                    risk_setup_name}_{scale_setup_name}"

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
                    'max_health_factor': risk_setup['max_health_factor'],

                    # Scale setup parameters
                    'num_vaults': scale_setup['num_vaults'],

                    # Metadata
                    'scenario_description': (
                        f"{price_scenario['description']} with {
                            risk_setup['description']} "
                        f"at {scale_setup['description']}"
                    )
                })

                scenarios[scenario_name] = scenario_params

    return scenarios
