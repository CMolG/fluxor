package com.javadaba.platform.shared;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Objects;

public record Cost(BigDecimal credits) {

    public static final Cost ZERO = new Cost(BigDecimal.ZERO);

    public Cost {
        Objects.requireNonNull(credits, "credits");
        if (credits.signum() < 0) {
            throw new IllegalArgumentException("Cost credits cannot be negative");
        }
        credits = credits.setScale(6, RoundingMode.HALF_UP);
    }

    public static Cost of(String credits) {
        return new Cost(new BigDecimal(credits));
    }

    public Cost plus(Cost other) {
        return new Cost(credits.add(other.credits));
    }

    public Cost multiply(BigDecimal multiplier) {
        if (multiplier.signum() < 0) {
            throw new IllegalArgumentException("Cost multiplier cannot be negative");
        }
        return new Cost(credits.multiply(multiplier));
    }
}
