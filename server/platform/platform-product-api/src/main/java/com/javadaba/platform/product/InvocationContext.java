package com.javadaba.platform.product;

import com.javadaba.platform.shared.ApiKeyId;
import com.javadaba.platform.shared.InvocationId;
import com.javadaba.platform.shared.OrganizationId;

import java.util.Map;

public record InvocationContext(
        InvocationId invocationId,
        OrganizationId organizationId,
        ApiKeyId apiKeyId,
        Map<String, Object> attributes) {
    public InvocationContext {
        attributes = Map.copyOf(attributes == null ? Map.of() : attributes);
    }

    public static InvocationContext anonymous() {
        return new InvocationContext(InvocationId.newId(), null, null, Map.of());
    }
}
