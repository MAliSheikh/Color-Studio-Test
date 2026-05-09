-- Task 1A: PostgreSQL Schema Design

-- Create brands table
CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create customers table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create products table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sku VARCHAR(100) NOT NULL CHECK (sku ~ '^[A-Za-z0-9_\-]+$'),
    category VARCHAR(100) NOT NULL,
    color VARCHAR(50),
    weight_grams DECIMAL(10, 2),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(brand_id, sku),
    UNIQUE(brand_id, id) -- Required for composite FK in order_items
);

-- Create orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'shipped', 'cancelled', 'refunded')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(brand_id, id) -- Required for composite FK in order_items
);

-- Create order items table
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL,
    order_id UUID NOT NULL,
    product_id UUID NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id, order_id) REFERENCES orders(brand_id, id) ON DELETE CASCADE,
    FOREIGN KEY (brand_id, product_id) REFERENCES products(brand_id, id) ON DELETE RESTRICT
);

-- Create raw materials table
CREATE TABLE raw_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_code VARCHAR(100) UNIQUE,
    name VARCHAR(255) NOT NULL,
    unit_of_measure VARCHAR(50) NOT NULL,
    current_stock_quantity DECIMAL(10, 3) NOT NULL DEFAULT 0 CHECK (current_stock_quantity >= 0),
    reorder_level DECIMAL(10, 3) NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
    cost_per_unit DECIMAL(10, 4) NOT NULL CHECK (cost_per_unit >= 0),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create formulations table
CREATE TABLE formulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL DEFAULT '1.0',
    notes TEXT,
    is_current_production BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, version)
);

-- Create formulation ingredients table
CREATE TABLE formulation_ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formulation_id UUID NOT NULL REFERENCES formulations(id) ON DELETE CASCADE,
    raw_material_id UUID NOT NULL REFERENCES raw_materials(id) ON DELETE RESTRICT,
    quantity DECIMAL(10, 4) NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(formulation_id, raw_material_id)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Fast lookup for products by brand and category
CREATE INDEX idx_products_brand_category ON products(brand_id, category);

-- Fast lookup for orders by customer and brand
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_brand_id ON orders(brand_id);

-- Fast lookup for items within an order
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

-- Fast lookup for formulations of a product
CREATE INDEX idx_formulations_product_id ON formulations(product_id);

-- Fast lookup for ingredients in a formulation
CREATE INDEX idx_formulation_ingredients_formulation_id ON formulation_ingredients(formulation_id);
CREATE INDEX idx_formulation_ingredients_raw_material_id ON formulation_ingredients(raw_material_id);
