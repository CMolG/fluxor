package com.javadaba.contexts.fluxor.application;

import jakarta.enterprise.context.ApplicationScoped;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Consumer;

/**
 * In-process, room-per-account pub/sub hub -- "el REST persiste, el broadcaster difunde" (plan
 * #19, Task 6 Step 2). Built here in Task 4 (earlier than the plan's literal Task 6 file list)
 * because {@code TaskBacklogService}/{@code FlowSyncService}/{@code RunMonitorService} (Task 4/5)
 * already need to call {@link #publish} on every write -- WITHOUT any WS listener subscribed yet,
 * {@link #publish} is a harmless no-op, so this ordering costs nothing. Task 6 is where {@code
 * FluxorRelaySocket} actually calls {@link #subscribe} per WS connection and adds device presence
 * on top; documented explicitly as a divergence in the Task 4 commit/report.
 *
 * <p>Single-instance state (same caveat class as {@code DevicePairingService}'s lockout counters):
 * a subscriber only receives events published on the SAME app-api process. Fine for today's single
 * instance; multi-instance would need a real pub/sub backbone (Redis Streams/pub-sub) -- BACKLOG.
 */
@ApplicationScoped
public class RelayBroadcaster {

    private final Map<UUID, List<Consumer<RelayEvent>>> subscribers = new ConcurrentHashMap<>();

    /** Returns a handle whose {@code close()} unsubscribes -- callers (Task 6's WS resource) use
     *  try-with-resources or close it on WS disconnect. */
    public AutoCloseable subscribe(UUID accountId, Consumer<RelayEvent> listener) {
        List<Consumer<RelayEvent>> room = subscribers.computeIfAbsent(accountId, key -> new CopyOnWriteArrayList<>());
        room.add(listener);
        return () -> room.remove(listener);
    }

    public void publish(UUID accountId, String type, Map<String, Object> payload) {
        List<Consumer<RelayEvent>> room = subscribers.get(accountId);
        if (room == null || room.isEmpty()) {
            return;
        }
        RelayEvent event = new RelayEvent(type, payload);
        for (Consumer<RelayEvent> listener : room) {
            listener.accept(event);
        }
    }

    /** Number of connected listeners for {@code accountId} -- used by Task 6 for {@code
     *  device.presence} (a device is "online" if the WS room has a live connection). */
    public int subscriberCount(UUID accountId) {
        List<Consumer<RelayEvent>> room = subscribers.get(accountId);
        return room == null ? 0 : room.size();
    }
}
