def derive_signals(signal):
    """Convert raw behavioral percentages into explainable signal types."""
    spend = float(signal.get("spending_change_pct") or 0)
    save = float(signal.get("savings_contribution_change_pct") or 0)
    login = float(signal.get("app_login_change_pct") or 0)
    unusual = bool(signal.get("unusual_withdrawal_flag"))

    out = []
    if save <= -40:
        out.append({"type": "Savings contribution drop", "severity": "High", "change": save})
    elif save <= -20:
        out.append({"type": "Savings contribution decline", "severity": "Medium", "change": save})
    elif save >= 25:
        out.append({"type": "Savings contribution growth", "severity": "Low", "change": save})

    if spend >= 40:
        out.append({"type": "Spending increase", "severity": "Medium", "change": spend})
    elif spend <= -30:
        out.append({"type": "Spending decrease", "severity": "Low", "change": spend})

    if login <= -50:
        out.append({"type": "App engagement decline", "severity": "Medium", "change": login})
    elif login >= 40:
        out.append({"type": "App engagement increase", "severity": "Low", "change": login})

    if unusual:
        out.append({"type": "Unusual withdrawal", "severity": "High", "change": None})

    if not out:
        out.append({"type": "No strong behavioral signal", "severity": "Low", "change": 0})
    return out


def channel_scores(customer, engagements):
    channels = ["Mobile App Push", "Email", "SMS", "WhatsApp"]
    scores = {channel: 0.0 for channel in channels}
    for engagement in engagements:
        channel = engagement.get("selected_channel")
        if channel in scores:
            scores[channel] += 1
            scores[channel] += 2 * int(bool(engagement.get("clicked")))
            scores[channel] += 3 * int(bool(engagement.get("converted")))
    preferred = customer.get("preferred_channel")
    if preferred in scores:
        scores[preferred] += 3
    total = sum(scores.values()) or 1
    return {channel: round(score / total * 100, 1) for channel, score in scores.items()}
