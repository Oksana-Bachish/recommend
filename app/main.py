import os
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from app.schemas import ProductRecommendation


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = await asyncpg.create_pool(
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST'),
        port=int(os.getenv('POSTGRES_PORT', 5432))
    )
    yield
    await app.state.db_pool.close()


app = FastAPI(title="Shop Recommendations API", lifespan=lifespan)

allowed_origins_raw = os.getenv('ALLOWED_ORIGINS', 'http://127.0.0.1:8000,http://localhost:8000')

origins = [origin.strip() for origin in allowed_origins_raw.split(',')]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/recommendations/{product_slug}", response_model=List[ProductRecommendation])
async def get_recommendations(product_slug: str, limit: int = Query(4, le=10)):
    pool = app.state.db_pool
    async with pool.acquire() as connection:
        product = await connection.fetchrow(
            'SELECT category_id, id FROM products WHERE slug = $1;', product_slug
        )

        if not product:
            raise HTTPException(status_code=404, detail='Товар не найден')

        category_id = product['category_id']
        current_id = product['id']

        if category_id is None:
            recommended_items = await connection.fetch(
                'SELECT id, name, price, image, category_id, slug FROM products WHERE id != $1 '
                'ORDER BY RANDOM() LIMIT $2', current_id, limit
            )
        else:
            recommended_items = await connection.fetch(
                'SELECT id, name, price, image, category_id, slug FROM products '
                'WHERE category_id = $1 AND id != $2 ORDER BY RANDOM() LIMIT $3',
                category_id, current_id, limit
            )

    return [dict(item) for item in recommended_items]
