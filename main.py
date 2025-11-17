import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import db, create_document, get_documents
from schemas import Product as ProductSchema
from bson import ObjectId

app = FastAPI(title="Vollara Products API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class ProductIn(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
    sku: Optional[str] = None
    images: Optional[List[str]] = None
    features: Optional[List[str]] = None
    slug: Optional[str] = None
    brand: Optional[str] = "Vollara"


def _serialize(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if doc.get("_id"):
        doc["id"] = str(doc.pop("_id"))
    # Convert any ObjectId nested just in case
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc


@app.get("/")
def read_root():
    return {"message": "Vollara Products Backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Seed a few sample products if collection empty
@app.on_event("startup")
async def seed_products():
    try:
        if db is None:
            return
        count = db["product"].count_documents({})
        if count == 0:
            samples: List[ProductIn] = [
                ProductIn(
                    title="Air & Surface Pro",
                    slug="air-and-surface-pro",
                    description="Advanced active air and surface purification for homes and businesses.",
                    price=799.0,
                    category="Air Purifier",
                    images=[
                        "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=1200&q=80&auto=format&fit=crop"
                    ],
                    features=[
                        "ActivePure Technology",
                        "Covers large areas",
                        "Whisper-quiet operation"
                    ],
                ),
                ProductIn(
                    title="FreshAir Personal",
                    slug="freshair-personal",
                    description="Wearable personal air purifier for on-the-go protection.",
                    price=199.0,
                    category="Wearable",
                    images=[
                        "https://images.unsplash.com/photo-1505740106531-4243f3831c78?w=1200&q=80&auto=format&fit=crop"
                    ],
                    features=[
                        "Lightweight and portable",
                        "USB rechargeable",
                        "Personal clean-air zone"
                    ],
                ),
                ProductIn(
                    title="Hydration System",
                    slug="living-water",
                    description="At-home water ionization and filtration for better-tasting water.",
                    price=1299.0,
                    category="Water",
                    images=[
                        "https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=1200&q=80&auto=format&fit=crop"
                    ],
                    features=[
                        "Multiple pH levels",
                        "Advanced filtration",
                        "Easy-install countertop"
                    ],
                ),
            ]
            for s in samples:
                create_document("product", ProductSchema(**s.model_dump()))
    except Exception:
        # Ignore seed errors to avoid blocking startup
        pass


@app.get("/api/products")
def list_products(limit: Optional[int] = None, category: Optional[str] = None):
    try:
        filter_q = {}
        if category:
            filter_q["category"] = category
        docs = get_documents("product", filter_q, limit)
        return [_serialize(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{slug}")
def get_product(slug: str):
    try:
        doc = db["product"].find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        return _serialize(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products", status_code=201)
def create_product(product: ProductIn):
    try:
        # ensure slug
        data = product.model_dump()
        if not data.get("slug"):
            data["slug"] = (
                data["title"].lower().strip().replace(" ", "-").replace("&", "and")
            )
        pid = create_document("product", ProductSchema(**data))
        doc = db["product"].find_one({"_id": ObjectId(pid)})
        return _serialize(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
