package com.javadaba.apps.fluxor.local;

import com.javadaba.contexts.fluxor.application.HarnessEnrollmentService;
import com.javadaba.contexts.fluxor.domain.ports.FluxorDeviceRepository;
import com.javadaba.contexts.fluxor.domain.ports.HarnessEnrollmentRepository;
import jakarta.annotation.Priority;
import jakarta.inject.Singleton;
import jakarta.enterprise.inject.Alternative;
import jakarta.inject.Inject;

/**
 * Enrollment in Fluxor Local. The Cloud edition mints a one-time code through its MCP and the
 * machine trades it for a device token; here that still works ({@code harness.bootstrap}), and in
 * addition the server accepts one fixed code, {@link LocalSettings#effectiveEnrollmentCode()}, so
 * {@code fluxor-sync init --enroll <code> --server http://127.0.0.1:18191/api} works with no MCP
 * client at all. The fixed code is the token when {@code FLUXOR_LOCAL_TOKEN} is set, so only
 * whoever holds the token can enroll a machine.
 */
@Alternative
@Priority(1)
@Singleton
public class LocalEnrollmentService extends HarnessEnrollmentService {

    private final LocalSettings settings;

    @Inject
    public LocalEnrollmentService(HarnessEnrollmentRepository enrollments, FluxorDeviceRepository devices,
            LocalSettings settings) {
        super(enrollments, devices);
        this.settings = settings;
    }

    @Override
    public Enrolled redeem(String code, String hostname) {
        if (code != null && LocalAuth.matches(settings.effectiveEnrollmentCode(), code.trim())) {
            return super.redeem(mint(settings.accountId()).code(), hostname);
        }
        return super.redeem(code, hostname);
    }
}
