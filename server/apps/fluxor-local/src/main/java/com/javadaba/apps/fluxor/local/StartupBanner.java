package com.javadaba.apps.fluxor.local;

import io.quarkus.runtime.StartupEvent;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;
import org.jboss.logging.Logger;

/** Says on startup how this server is reached and how a machine enrolls, so nobody has to guess. */
@ApplicationScoped
public class StartupBanner {

    private static final Logger LOG = Logger.getLogger(StartupBanner.class);

    private final LocalSettings settings;

    public StartupBanner(LocalSettings settings) {
        this.settings = settings;
    }

    void onStart(@Observes StartupEvent event) {
        boolean secured = settings.requiredToken().isPresent();
        LOG.infof("Fluxor Local is up. API: %s. Authentication: %s.", settings.publicUrl(),
                secured ? "FLUXOR_LOCAL_TOKEN required on /fluxor/mcp"
                        : "off (no FLUXOR_LOCAL_TOKEN): keep it on the loopback");
        LOG.infof("Enroll a machine: python3 fluxor-sync.py init --server %s --enroll %s --project <project-id>",
                settings.publicUrl(), secured ? "<FLUXOR_LOCAL_TOKEN>" : settings.effectiveEnrollmentCode());
    }
}
