def get_wash_recommendation(cloth_name, service_name):

    cloth = cloth_name.lower()
    service = service_name.lower()

    # Default
    recommendation = {
        "water": "Cold",
        "cycle": "Normal",
        "detergent": "Regular Detergent",
        "dry": "Air Dry"
    }

    if "silk" in cloth:
        recommendation.update({
            "water": "Cold",
            "cycle": "Gentle",
            "detergent": "Mild Detergent",
            "dry": "Air Dry"
        })

    elif "cotton" in cloth:
        recommendation.update({
            "water": "Warm",
            "cycle": "Normal",
            "detergent": "Strong Detergent",
            "dry": "Machine Dry"
        })

    elif "denim" in cloth:
        recommendation.update({
            "water": "Cold",
            "cycle": "Heavy",
            "detergent": "Regular Detergent",
            "dry": "Air Dry"
        })

    elif "wool" in cloth:
        recommendation.update({
            "water": "Cold",
            "cycle": "Gentle",
            "detergent": "Wool Detergent",
            "dry": "Flat Dry"
        })

    # Service influence
    if "dry clean" in service:
        recommendation.update({
            "water": "No Water",
            "cycle": "Dry Clean",
            "detergent": "Solvent",
            "dry": "Professional Dry"
        })

    return recommendation
