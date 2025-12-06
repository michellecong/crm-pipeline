import type { Product } from "../types/api";
import "./Section.css";

interface ProductsSectionProps {
  products: Product[];
}

export default function ProductsSection({ products }: ProductsSectionProps) {
  return (
    <section className="section">
      <h2 className="section-title">Product Catalog ({products.length})</h2>
      <div className="products-grid">
        {products.map((product, index) => (
          <div key={index} className="product-card">
            <h3 className="product-name">{product.product_name}</h3>
            <p className="product-description">{product.description}</p>
            {product.source_url && (
              <a
                href={product.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="product-link"
              >
                View Details →
              </a>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
