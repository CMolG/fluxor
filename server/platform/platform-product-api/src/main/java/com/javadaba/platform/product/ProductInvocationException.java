package com.javadaba.platform.product;

public class ProductInvocationException extends RuntimeException {
    public ProductInvocationException(String message) {
        super(message);
    }

    public ProductInvocationException(String message, Throwable cause) {
        super(message, cause);
    }
}
