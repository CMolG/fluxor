package com.javadaba.contexts.fluxor.application;

import java.util.Map;

/**
 * A server-centric event pushed to WS-connected consoles/devices (plan #19, Task 6) -- the REST
 * layer (services in THIS package) persists first, then publishes; the WS relay ({@code
 * FluxorRelaySocket}, Task 6) only forwards, never originates state. {@code type} is one of
 * {@code task.updated}, {@code flow.updated}, {@code run.opened}, {@code run.event}, {@code
 * run.closed}, {@code device.presence} (documented in the Task 8 contract).
 */
public record RelayEvent(String type, Map<String, Object> payload) {
}
