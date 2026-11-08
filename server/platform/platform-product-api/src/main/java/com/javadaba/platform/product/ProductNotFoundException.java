package com.javadaba.platform.product;

import com.javadaba.platform.shared.ProductSlug;

public class ProductNotFoundException extends RuntimeException {
    public ProductNotFoundException(ProductSlug slug) {
        super("Product not found: " + slug.value());
    }
}
