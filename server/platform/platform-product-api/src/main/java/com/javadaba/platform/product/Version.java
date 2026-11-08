package com.javadaba.platform.product;

public record Version(int major, int minor) {
    public Version {
        if (major < 1) {
            throw new IllegalArgumentException("Major version must be >= 1");
        }
        if (minor < 0) {
            throw new IllegalArgumentException("Minor version cannot be negative");
        }
    }

    @Override
    public String toString() {
        return major + "." + minor;
    }
}
