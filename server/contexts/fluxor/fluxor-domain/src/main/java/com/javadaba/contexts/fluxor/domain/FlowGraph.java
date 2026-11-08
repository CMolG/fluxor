package com.javadaba.contexts.fluxor.domain;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Set;
import java.util.function.Function;

/**
 * The graph rules a {@code fluxor-flow} shares between its compiler ({@link FlowCompiler}) and its
 * validator ({@link FlowDefinitionValidator}), so a canvas the designer compiles and a document
 * someone imports are held to the same ones. Reimplemented from fluxor-ide {@code feat/cockpit}
 * (Apache-2.0): {@code topoSortAgenticSteps} and {@code clampLoopIterations}
 * ({@code src/types/harness.ts}) and the loop checks of {@code compileFlowFromCanvas}
 * ({@code src/renderer/lib/harness-compiler.ts}). Contract: {@code doc://contracts/fluxor-flow}.
 */
final class FlowGraph {

    static final int LOOP_DEFAULT_ITERATIONS = 3;
    static final int LOOP_MAX_ITERATIONS = 50;

    private FlowGraph() {
    }

    /** A bounded loop-back edge: after {@code sourceStepId}, control returns to {@code targetStepId}. */
    record Loop(String id, String sourceStepId, String targetStepId) {
    }

    /** The format's step order: Kahn's algorithm, always taking the ready step with the lowest id. */
    static List<String> order(Collection<String> ids, Map<String, List<String>> dependsOn) {
        Map<String, Integer> waiting = new HashMap<>();
        Map<String, List<String>> next = new HashMap<>();
        PriorityQueue<String> ready = new PriorityQueue<>();
        for (String id : ids) {
            List<String> deps = dependsOn.getOrDefault(id, List.of());
            waiting.put(id, deps.size());
            for (String dep : deps) {
                next.computeIfAbsent(dep, k -> new ArrayList<>()).add(id);
            }
            if (deps.isEmpty()) {
                ready.add(id);
            }
        }
        List<String> ordered = new ArrayList<>();
        while (!ready.isEmpty()) {
            String id = ready.poll();
            ordered.add(id);
            for (String child : next.getOrDefault(id, List.of())) {
                if (waiting.merge(child, -1, Integer::sum) == 0) {
                    ready.add(child);
                }
            }
        }
        return ordered;
    }

    /** The first circle found by following {@code next}, as a path that ends where it starts; empty if none. */
    static List<String> cycle(Collection<String> ids, Map<String, List<String>> next) {
        Set<String> done = new LinkedHashSet<>();
        for (String start : ids) {
            List<String> found = walk(start, next, done, new LinkedHashSet<>(), new ArrayDeque<>());
            if (!found.isEmpty()) {
                return found;
            }
        }
        return List.of();
    }

    private static List<String> walk(String id, Map<String, List<String>> next, Set<String> done, Set<String> onPath,
            Deque<String> path) {
        if (onPath.contains(id)) {
            List<String> circle = new ArrayList<>();
            boolean started = false;
            for (String node : path) {
                started |= node.equals(id);
                if (started) {
                    circle.add(node);
                }
            }
            circle.add(id);
            return circle;
        }
        if (!done.add(id)) {
            return List.of();
        }
        onPath.add(id);
        path.addLast(id);
        for (String child : next.getOrDefault(id, List.of())) {
            List<String> found = walk(child, next, done, onPath, path);
            if (!found.isEmpty()) {
                return found;
            }
        }
        path.removeLast();
        onPath.remove(id);
        return List.of();
    }

    static Set<String> reachable(String from, Map<String, List<String>> adjacency) {
        Set<String> seen = new LinkedHashSet<>();
        Deque<String> stack = new ArrayDeque<>(List.of(from));
        while (!stack.isEmpty()) {
            String id = stack.pop();
            if (seen.add(id)) {
                stack.addAll(adjacency.getOrDefault(id, List.of()));
            }
        }
        return seen;
    }

    /**
     * What is wrong with a flow's loops, in words: a loop runs back to an EARLIER step (never to
     * itself), and two loops never share a step (no nesting, no overlap). A loop's body is every step
     * on a forward path from its target to its source.
     */
    static List<String> loopProblems(List<Loop> loops, Map<String, List<String>> next,
            Map<String, List<String>> dependsOn, Function<String, String> label) {
        List<String> problems = new ArrayList<>();
        Map<String, Set<String>> bodies = new LinkedHashMap<>();
        for (Loop loop : loops) {
            if (loop.sourceStepId().equals(loop.targetStepId())) {
                problems.add("A loop cannot run a step back to itself (" + label.apply(loop.sourceStepId()) + ").");
                continue;
            }
            Set<String> fromTarget = reachable(loop.targetStepId(), next);
            if (!fromTarget.contains(loop.sourceStepId())) {
                problems.add("A loop must run back to an earlier step: " + label.apply(loop.targetStepId())
                        + " does not lead to " + label.apply(loop.sourceStepId()) + ".");
                continue;
            }
            Set<String> body = new LinkedHashSet<>(fromTarget);
            body.retainAll(reachable(loop.sourceStepId(), dependsOn));
            for (Map.Entry<String, Set<String>> other : bodies.entrySet()) {
                List<String> shared = body.stream().filter(other.getValue()::contains).map(label).toList();
                if (!shared.isEmpty()) {
                    problems.add("Loops " + other.getKey() + " and " + loop.id() + " both repeat "
                            + String.join(", ", shared) + ": loops cannot be nested or overlap.");
                }
            }
            bodies.put(loop.id(), body);
        }
        return problems;
    }

    /** The IDE's clamp: whole passes, 1..50, and 3 when the value is not a number. */
    static int clampIterations(Object value) {
        int passes = value instanceof Number n && Double.isFinite(n.doubleValue())
                ? (int) Math.floor(n.doubleValue())
                : LOOP_DEFAULT_ITERATIONS;
        return Math.min(LOOP_MAX_ITERATIONS, Math.max(1, passes));
    }
}
