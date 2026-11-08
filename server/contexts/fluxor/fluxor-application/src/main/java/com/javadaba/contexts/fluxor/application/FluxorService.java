package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.Release;
import com.javadaba.contexts.fluxor.domain.Ticket;
import com.javadaba.contexts.fluxor.domain.TicketStatus;
import com.javadaba.contexts.fluxor.domain.ports.ReleaseRepository;
import com.javadaba.contexts.fluxor.domain.ports.TicketRepository;
import jakarta.enterprise.context.ApplicationScoped;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** Fluxor business surface inside Javadaba: support tickets and downloadable releases. */
@ApplicationScoped
public class FluxorService {

    private final TicketRepository tickets;
    private final ReleaseRepository releases;

    public FluxorService(TicketRepository tickets, ReleaseRepository releases) {
        this.tickets = tickets;
        this.releases = releases;
    }

    public Ticket openTicket(String subject, String body, String email) {
        Ticket ticket = new Ticket(UUID.randomUUID(), subject, body, email, TicketStatus.OPEN, Instant.now());
        tickets.save(ticket);
        return ticket;
    }

    public Optional<Ticket> ticket(UUID id) {
        return tickets.findById(id);
    }

    public List<Release> releases() {
        return releases.all();
    }

    public Optional<Release> latest(String platform) {
        return releases.latest(platform);
    }
}
