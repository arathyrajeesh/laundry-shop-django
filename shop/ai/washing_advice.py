def suggest_washing(cloth, stain):
    if cloth == "Silk":
        return "Dry Cleaning Only"

    if cloth == "Denim":
        if stain == "Oil":
            return "Cold Wash + Degreaser"
        return "Cold Wash"

    if cloth == "Cotton":
        if stain == "Food":
            return "Warm Wash + Detergent"
        return "Normal Wash"

    return "Manual Inspection Required"
