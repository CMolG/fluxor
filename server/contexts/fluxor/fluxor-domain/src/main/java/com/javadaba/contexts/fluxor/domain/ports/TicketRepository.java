package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.Ticket;

import java.util.Optional;
import java.util.UUID;

public interface TicketRepository {

    void save(Ticket ticket);

    Optional<Ticket> findById(UUID id);
}
