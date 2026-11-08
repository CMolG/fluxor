package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.Pack;
import com.javadaba.contexts.fluxor.domain.ports.PackRepository;

import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

final class FakePackRepository implements PackRepository {
    private final Map<String, Pack> packs = new LinkedHashMap<>();
    private final Map<String, Set<UUID>> attachments = new LinkedHashMap<>();

    private static String key(UUID accountId, String packId) {
        return accountId + "/" + packId;
    }

    @Override
    public void publish(Pack pack, UUID projectId) {
        String key = key(pack.accountId(), pack.packId());
        packs.put(key, pack);
        attachments.computeIfAbsent(key, k -> new HashSet<>()).add(projectId);
    }

    @Override
    public boolean detach(UUID accountId, String packId, UUID projectId) {
        Set<UUID> projects = attachments.get(key(accountId, packId));
        return projects != null && projects.remove(projectId);
    }

    @Override
    public boolean delete(UUID accountId, String packId) {
        attachments.remove(key(accountId, packId));
        return packs.remove(key(accountId, packId)) != null;
    }

    @Override
    public void deleteRole(UUID accountId, String role) {
        packs.values().stream().filter(p -> p.accountId().equals(accountId) && p.role().equals(role))
                .map(Pack::packId).toList().forEach(id -> delete(accountId, id));
    }

    @Override
    public List<Pack> findAttached(UUID projectId) {
        return packs.entrySet().stream()
                .filter(e -> attachments.getOrDefault(e.getKey(), Set.of()).contains(projectId))
                .map(Map.Entry::getValue).sorted(Comparator.comparing(Pack::packId)).toList();
    }
}
