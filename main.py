from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import re

app = FastAPI()

# WooCommerce API credentials
WC_API_URL = "https://marmorkrafts.com/wp-json/wc/v3"
WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"

# Utility to strip HTML tags
def strip_html(text: str) -> str:
    return re.sub(r'<[^>]*>', '', text or '')

# Utility to get product variations
def get_variations(product_id: int):
    url = f"{WC_API_URL}/products/{product_id}/variations?per_page=50"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))
    if response.status_code != 200:
        return []
    variations = response.json()
    variation_list = []
    for v in variations:
        variation_list.append({
            "id": v["id"],
            "price": v.get("price"),
            "attributes": v.get("attributes", []),
            "image": v["image"]["src"] if v.get("image") else None
        })
    return variation_list

@app.get("/products")
def get_products(query: str = "", color: str = "", exclude_marble: bool = False):
    url = f"{WC_API_URL}/products?search={query}&per_page=20"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content={"error": "Failed to fetch products"})

    data = response.json()

    products = []

    for item in data:
        name = item["name"].lower()
        short_desc = item.get("short_description", "").lower()
        long_desc = strip_html(item.get("description", "")).lower()

        # Skip if marble filter enabled and "marble" is found
        if exclude_marble and ("marble" in name or "marble" in short_desc or "marble" in long_desc):
            continue

        # Get variations (e.g., for colors)
        variations = get_variations(item["id"])

        # Filter variations by color if requested
        if color:
            variations = [
                v for v in variations
                if any(attr["name"].lower() == "color" and attr["option"].lower() == color.lower()
                       for attr in v["attributes"])
            ]
            if not variations:
                continue  # No matching color → skip product

        # Build product object
        products.append({
            "name": item["name"],
            "url": item["permalink"],
            "image": item["images"][0]["src"] if item.get("images") else "",
            "price": item.get("price"),
            "description": item.get("short_description", ""),
            "variations": variations
        })

    # ✅ Copilot-friendly response
    if not products:
        return {
            "message": "No matching products found. There may be no products without marble or in the specified color.",
            "products": []
        }

    return {
        "message": "Matching products found.",
        "products": products
    }