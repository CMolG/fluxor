package com.javadaba.platform.product;

public interface Product {

    ProductDescriptor descriptor();

    ProductResult invoke(ProductInput input, InvocationContext ctx);
}
