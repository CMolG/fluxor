package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.Release;

import java.util.List;
import java.util.Optional;

public interface ReleaseRepository {

    List<Release> all();

    Optional<Release> latest(String platform);
}
