package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.UUID;

/** A Fluxor support ticket (the IDE is a downloadable executable; support runs here). */
public record Ticket(UUID id, String subject, String body, String email, TicketStatus status, Instant createdAt) {
}
