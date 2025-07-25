
from fastapi import FastAPI
import requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, Header, HTTPException

app = FastAPI()


@app.get("/")
def home():
    return {"message": "It works on Railway!!"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://testingmarmorkrafts.store"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# For DEv
WC_API_URL = "https://testingmarmorkrafts.store/wp-json/wc/v3"
WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"

# # For Prod
# WC_API_URL = "https://marmorkrafts.com/wp-json/wc/v3"
# WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
# WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"

@app.get("/order-status/{order_id}")
def get_order_status(order_id: int, x_user_email: str = Header(None)):
    if not x_user_email:
        raise HTTPException(status_code=401, detail="Missing X-User-Email header.")

    # Fetch order from WooCommerce
    order_url = f"{WC_API_URL}/orders/{order_id}"
    response = requests.get(order_url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if response.status_code != 200:
        return JSONResponse(
            status_code=response.status_code,
            content={"error": "Failed to fetch order from WooCommerce."}
        )

    order_data = response.json()

    # Validate ownership by matching email
    billing_email = order_data.get("billing", {}).get("email", "")
    if billing_email.lower() != x_user_email.lower():
        return JSONResponse(status_code=403, content={"error": "Unauthorized – this order does not belong to you."})

    # Extract tracking number
    tracking_number = "Not available"
    for meta in order_data.get("meta_data", []):
        if meta.get("key") == "_wc_shipment_tracking_items":
            items = meta.get("value", [])
            if isinstance(items, list) and items:
                tracking_number = items[0].get("tracking_number", "Not available")
            break

    # Return formatted schema
    return JSONResponse(content={
        "@context": "https://schema.org",
        "@type": "Order",
        "order_number": order_data.get("number"),
        "status": order_data.get("status"),
        "currency": order_data.get("currency"),
        "total": order_data.get("total"),
        "shipping_method": order_data["shipping_lines"][0]["method_title"] if order_data["shipping_lines"] else "",
        "billing_address": order_data.get("billing"),
        "shipping_address": order_data.get("shipping"),
        "tracking_number": tracking_number,
        "order_date": order_data.get("date_created"),
        "line_items": [
            {
                "name": item["name"],
                "quantity": item["quantity"],
                "price": item["price"]
            } for item in order_data.get("line_items", [])
        ]
    })
