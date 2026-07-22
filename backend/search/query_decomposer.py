import re
from typing import List, Dict, Any, Optional

def extract_product_constraints(query: str) -> Dict[str, Any]:
    """
    Extracts structured constraint metadata from product shopping queries.
    """
    query_lower = query.lower()
    constraints = {
        "is_product_query": False,
        "category": None,
        "budget_max": None,
        "currency": "INR" if ("₹" in query or "rs" in query_lower or "rupees" in query_lower or "india" in query_lower) else "USD",
        "market": "India" if ("india" in query_lower or "in india" in query_lower or "₹" in query or "rs" in query_lower) else "Global"
    }

    # Category detection
    if any(term in query_lower for term in ["phone", "mobile", "smartphone", "iphone", "galaxy", "oneplus"]):
        constraints["category"] = "smartphone"
        constraints["is_product_query"] = True
    elif any(term in query_lower for term in ["laptop", "macbook", "pc"]):
        constraints["category"] = "laptop"
        constraints["is_product_query"] = True
    elif any(term in query_lower for term in ["tv", "television", "watch", "camera", "headphone", "earbuds"]):
        constraints["category"] = "electronics"
        constraints["is_product_query"] = True

    # Budget extraction (e.g. under 70,000 or under ₹70,000 or below 50000)
    match_budget = re.search(r'(?:under|below|around|sub|less than)\s*([₹rs\.\s]*\d+[\d,]*k?)', query_lower)
    if match_budget:
        raw_val = match_budget.group(1).replace("₹", "").replace("rs", "").replace(".", "").replace(",", "").strip()
        if raw_val.endswith("k"):
            try:
                num = int(float(raw_val[:-1]) * 1000)
                constraints["budget_max"] = num
            except ValueError:
                pass
        else:
            try:
                constraints["budget_max"] = int(raw_val)
            except ValueError:
                pass

    return constraints

def generate_targeted_product_queries(query: str, constraints: Dict[str, Any]) -> List[str]:
    """
    Generates targeted subqueries to improve discovery on reputable product review portals.
    """
    queries = [query]
    if not constraints.get("is_product_query"):
        return queries

    category = constraints.get("category", "phone")
    budget = constraints.get("budget_max")
    market = constraints.get("market", "")

    if category == "smartphone" and budget:
        queries.append(f"best smartphones under {budget} {market}".strip())
        queries.append(f"top mobile phones under {budget} India 91mobiles gadgets360 smartprix")
        queries.append(f"best phones under {budget} Rs India comparison review")
    elif category and market:
        queries.append(f"best {category} {market} comparison review")

    return queries
