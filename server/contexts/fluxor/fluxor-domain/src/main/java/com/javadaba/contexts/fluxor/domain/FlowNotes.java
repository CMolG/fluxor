package com.javadaba.contexts.fluxor.domain;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * What each step reads from the canvas's notes: the notes attached to it, and the notes reachable from them through
 * note-to-note links, whichever way each link was drawn. A note read as {@code primary-input} is the step's input;
 * every other note is context. Behaviour of fluxor-ide's mental digest, reimplemented and not copied. Contract:
 * {@code doc://contracts/fluxor-flow} §3.
 */
final class FlowNotes {

    /**
     * {@code context}: every note the step reads, note id to text, attached notes first. {@code inputs}: how those
     * notes are read, or null when {@code context} alone says all there is to say (no typed note, no primary input,
     * no link between notes).
     */
    record Reading(Map<String, String> context, Map<String, Object> inputs) {
    }

    private FlowNotes() {
    }

    static Map<String, Reading> read(FlowCanvas canvas) {
        Map<String, FlowCanvas.Note> notes = new LinkedHashMap<>();
        canvas.notes().forEach(note -> notes.put(note.id(), note));
        Map<String, List<String>> linked = new HashMap<>();
        List<FlowCanvas.Edge> noteLinks = new ArrayList<>();
        Map<String, Map<String, Boolean>> attached = new LinkedHashMap<>();
        canvas.steps().forEach(step -> attached.put(step.id(), new LinkedHashMap<>()));
        for (FlowCanvas.Edge edge : canvas.edges()) {
            if (!"attachment".equals(edge.kind())) {
                continue;
            }
            if (notes.containsKey(edge.source()) && notes.containsKey(edge.target())) {
                noteLinks.add(edge);
                linked.computeIfAbsent(edge.source(), id -> new ArrayList<>()).add(edge.target());
                linked.computeIfAbsent(edge.target(), id -> new ArrayList<>()).add(edge.source());
            } else if (attached.containsKey(edge.target()) && notes.containsKey(edge.source())) {
                attach(attached.get(edge.target()), edge.source(), edge);
            } else if (attached.containsKey(edge.source()) && notes.containsKey(edge.target())) {
                attach(attached.get(edge.source()), edge.target(), edge);
            }
        }
        Map<String, Reading> readings = new LinkedHashMap<>();
        attached.forEach((stepId, direct) -> readings.put(stepId, reading(direct, notes, linked, noteLinks)));
        return readings;
    }

    /** A note attached twice to one step is read once, and primary input wins. */
    private static void attach(Map<String, Boolean> direct, String noteId, FlowCanvas.Edge edge) {
        direct.merge(noteId, FlowCanvas.PRIMARY_INPUT.equals(edge.mode()), Boolean::logicalOr);
    }

    private static Reading reading(Map<String, Boolean> direct, Map<String, FlowCanvas.Note> notes,
            Map<String, List<String>> linked, List<FlowCanvas.Edge> noteLinks) {
        Set<String> reach = new LinkedHashSet<>(direct.keySet());
        Deque<String> queue = new ArrayDeque<>(direct.keySet());
        while (!queue.isEmpty()) {
            for (String next : linked.getOrDefault(queue.poll(), List.of())) {
                if (reach.add(next)) {
                    queue.add(next);
                }
            }
        }
        Map<String, String> context = new LinkedHashMap<>();
        reach.forEach(id -> context.put(id, notes.get(id).text()));
        Set<String> inherited = inheritedPrimary(direct, linked);
        return new Reading(context, inputsOf(reach, direct, inherited, notes, noteLinks));
    }

    /**
     * The notes a primary-input note reaches through notes that are not attached to the step. A note attached to the
     * step keeps its own mode, so the walk stops at it.
     */
    private static Set<String> inheritedPrimary(Map<String, Boolean> direct, Map<String, List<String>> linked) {
        Set<String> inherited = new HashSet<>();
        Deque<String> queue = new ArrayDeque<>();
        direct.forEach((id, primary) -> {
            if (primary) {
                queue.add(id);
            }
        });
        while (!queue.isEmpty()) {
            for (String next : linked.getOrDefault(queue.poll(), List.of())) {
                if (!direct.containsKey(next) && inherited.add(next)) {
                    queue.add(next);
                }
            }
        }
        return inherited;
    }

    private static Map<String, Object> inputsOf(Set<String> reach, Map<String, Boolean> direct, Set<String> inherited,
            Map<String, FlowCanvas.Note> notes, List<FlowCanvas.Edge> noteLinks) {
        List<String> primary = new ArrayList<>();
        List<String> context = new ArrayList<>();
        for (String id : reach) {
            boolean isPrimary = direct.containsKey(id) ? direct.get(id) : inherited.contains(id);
            (isPrimary ? primary : context).add(id);
        }
        List<List<String>> links = noteLinks.stream()
                .filter(edge -> reach.contains(edge.source()) && reach.contains(edge.target()))
                .map(edge -> List.of(edge.source(), edge.target()))
                .toList();
        boolean typed = reach.stream().anyMatch(id -> notes.get(id).type() != null);
        if (primary.isEmpty() && links.isEmpty() && !typed) {
            return null;
        }
        Map<String, Object> inputs = new LinkedHashMap<>();
        if (!primary.isEmpty()) {
            inputs.put("primaryInput", groups(primary, notes));
        }
        if (!context.isEmpty()) {
            inputs.put("context", groups(context, notes));
        }
        if (!links.isEmpty()) {
            inputs.put("links", links);
        }
        return inputs;
    }

    /** Groups note ids by type, in the order each type first appears; an untyped group has no {@code type} key. */
    private static List<Map<String, Object>> groups(List<String> ids, Map<String, FlowCanvas.Note> notes) {
        Map<String, List<String>> byType = new LinkedHashMap<>();
        ids.forEach(id -> byType.computeIfAbsent(typeOf(notes.get(id)), type -> new ArrayList<>()).add(id));
        List<Map<String, Object>> groups = new ArrayList<>();
        byType.forEach((type, group) -> {
            Map<String, Object> entry = new LinkedHashMap<>();
            if (!type.isEmpty()) {
                entry.put("type", type);
            }
            entry.put("notes", group);
            groups.add(entry);
        });
        return groups;
    }

    private static String typeOf(FlowCanvas.Note note) {
        return note.type() == null ? "" : note.type();
    }
}
