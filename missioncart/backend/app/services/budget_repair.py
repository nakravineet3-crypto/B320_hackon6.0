def repair_budget(cart_items: list, needs: list, budget_max: float, catalog: list) -> tuple:
    """6-step budget repair sequence.
    Returns (repaired_items, repair_log).
    """
    repair_log = []
    total = sum(i.get("total_cost", 0) for i in cart_items)

    if total <= budget_max:
        return cart_items, repair_log

    # STEP 1: Trim buffer — reduce packs by 1 for non-must_have items
    for item in cart_items:
        if total <= budget_max:
            break
        need = next(
            (n for n in needs if n.need_id == item.get("need_id")), None
        )
        if need and need.priority != "must_have":
            current_packs = item.get("packs_quantity", 1)
            if current_packs > 1:
                new_packs = current_packs - 1
                old_cost = item["total_cost"]
                item["packs_quantity"] = new_packs
                item["units_total"] = new_packs * item.get("pack_size", 1)
                item["total_cost"] = item.get("price", item.get("price_per_unit", 0)) * new_packs
                item["was_repaired"] = True
                item["repair_reason"] = "Buffer reduced"
                saved = old_cost - item["total_cost"]
                total -= saved
                repair_log.append({
                    "step": 1,
                    "action": f"Reduced {item.get('need_label', 'item')} buffer",
                    "saved": round(saved, 2),
                })

    if total <= budget_max:
        return cart_items, repair_log

    # STEP 2: Swap to cheaper equivalent (80% price)
    for i, item in enumerate(cart_items):
        if total <= budget_max:
            break
        need = next(
            (n for n in needs if n.need_id == item.get("need_id")), None
        )
        if not need or need.priority == "must_have":
            continue

        # Find cheaper alternative in same category
        item_price = item.get("price", item.get("price_per_unit", 999))
        cheaper = [
            p for p in catalog
            if p.get("category") == item.get("category")
            and p.get("price", 999) < item_price * 0.85
            and p.get("rating", 0) >= 3.5
            and p.get("stock_available", True)
        ]
        if cheaper:
            best = sorted(cheaper, key=lambda x: x.get("price", 999))[0]
            old_cost = item["total_cost"]
            packs = item.get("packs_quantity", 1)
            item["asin"] = best.get("asin")
            item["title"] = best.get("title")
            item["price"] = best.get("price", 0)
            item["price_per_unit"] = best.get("price", 0)
            item["total_cost"] = best.get("price", 0) * packs
            item["was_repaired"] = True
            item["repair_reason"] = "Swapped to cheaper equivalent"
            saved = old_cost - item["total_cost"]
            total -= saved
            repair_log.append({
                "step": 2,
                "action": f"Swapped {item.get('need_label', 'item')} to cheaper option",
                "saved": round(saved, 2),
            })

    if total <= budget_max:
        return cart_items, repair_log

    # STEP 3: Drop optional needs (cheapest first)
    optional_items = [
        i for i in cart_items
        if any(
            n.need_id == i.get("need_id") and n.priority == "optional"
            for n in needs
        )
    ]
    optional_items.sort(key=lambda x: x.get("total_cost", 0))

    for item in optional_items:
        if total <= budget_max:
            break
        total -= item.get("total_cost", 0)
        repair_log.append({
            "step": 3,
            "action": f"Removed optional: {item.get('need_label', 'item')}",
            "saved": round(item.get("total_cost", 0), 2),
        })
        cart_items = [
            i for i in cart_items if i.get("need_id") != item.get("need_id")
        ]

    if total <= budget_max:
        return cart_items, repair_log

    # STEP 4: Drop should_have needs (with announcement)
    should_items = [
        i for i in cart_items
        if any(
            n.need_id == i.get("need_id") and n.priority == "should_have"
            for n in needs
        )
    ]
    should_items.sort(key=lambda x: x.get("total_cost", 0))

    for item in should_items:
        if total <= budget_max:
            break
        total -= item.get("total_cost", 0)
        repair_log.append({
            "step": 4,
            "action": f"Removed {item.get('need_label', 'item')} to meet budget — consider adding back",
            "saved": round(item.get("total_cost", 0), 2),
        })
        cart_items = [
            i for i in cart_items if i.get("need_id") != item.get("need_id")
        ]

    # STEP 5: Never silently drop must_have
    if total > budget_max:
        repair_log.append({
            "step": 5,
            "action": "WARNING: Could not meet budget without dropping must-have items",
            "saved": 0,
        })

    return cart_items, repair_log
