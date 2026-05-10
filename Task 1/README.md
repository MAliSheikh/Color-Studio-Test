# Color Studio Technical Test

This repository contains the solutions for the technical test assignments. Each task is separated into its own directory.

## Task 1A: Schema Design

**Directory:** `task_1a_schema_design/`

**Description:**
A PostgreSQL database schema designed to support multiple cosmetics brands, a shared customer base, products, orders, raw materials, and product formulations (recipes).

**Key Design Decisions:**
- **Shared Customer Identity:** `customers` are defined at the top level so that any customer purchasing from any brand shares the same underlying record and UUID.
- **Brand Separation:** `orders` and `products` are linked to a specific `brand_id`. SKUs for products are constrained to be unique *per brand*, allowing different brands to theoretically have overlapping SKU systems without conflict.
- **Order Items:** We copy the `unit_price` at the time of purchase into `order_items` rather than just linking the product. This ensures historical orders remain accurate even if a product's price changes.
- **Formulations:** A separate `formulations` table allows for versioning over time (e.g., swapping out an ingredient for a new formulation of the same product SKU). The `formulation_ingredients` junction table maps the precise quantity of `raw_materials` needed.
- **Raw Materials:** Tracked globally (not tied to a specific brand) assuming centralized manufacturing/inventory for raw materials.
- **Data Integrity & Simplicity:** Essential data constraints (e.g., regex validation for SKU formatting and composite foreign keys) are enforced natively. Complex database triggers were intentionally avoided to maintain schema simplicity.
- **Soft Deletes:** Core tables (brands, customers, products, raw materials, formulations) utilize an `is_active` flag to support consistent soft deletion without losing relational history.

## Task 1B: Vector Knowledge Base

**Directory:** `task_1b_vector_knowledge_base/`

**Description:**
A Python script (`knowledge_base.py`) that reads a sample dataset of cosmetics packaging/formulation configurations, embeds them using a local open-source embedding model, and exposes a CLI for semantic search augmented by Groq.

**Tools & Design Decisions:**
- **Chunking Strategy:** Row-level chunking to keep each configuration intact.
- **Embeddings:** Uses `chromadb` default `all-MiniLM-L6-v2` model locally.
- **Vector Store:** `chromadb` for lightweight storage.
- **LLM/Chat:** Groq API provides answers based solely on retrieved context.

For installation and execution instructions, see the root `Readme.md`.
