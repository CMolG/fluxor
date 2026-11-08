package com.javadaba.contexts.fluxor.domain;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * The part of a CEET role's {@code interview/form.json} an interview kept by Fluxor online needs
 * (card://JAVA-285): its modules, sections and questions, in order. The form is the role skill's
 * file in the catalog ({@code ceet-core}'s {@code schemas/form.schema.json} is its contract), read
 * as a parsed JSON map so no reflection is involved.
 */
public record InterviewForm(String role, String formVersion, String title, List<Module> modules) {

    public record Module(String id, String title, boolean optional, List<Section> sections) {
    }

    public record Section(String id, String title, List<Question> questions) {
    }

    public record Question(String id, String prompt, String kind, boolean required, int minutes,
            List<String> probes) {
    }

    public List<Question> questions() {
        return modules.stream().flatMap(m -> m.sections().stream()).flatMap(s -> s.questions().stream()).toList();
    }

    public boolean has(String questionId) {
        return questions().stream().anyMatch(q -> q.id().equals(questionId));
    }

    /** Fails on a form that lacks what the interview reads: the catalog only holds validated forms. */
    public static InterviewForm of(Map<String, Object> form) {
        List<Module> modules = new ArrayList<>();
        for (Map<String, Object> module : maps(form, "modules")) {
            List<Section> sections = new ArrayList<>();
            for (Map<String, Object> section : maps(module, "sections")) {
                List<Question> questions = new ArrayList<>();
                for (Map<String, Object> question : maps(section, "questions")) {
                    questions.add(new Question(text(question, "id"), text(question, "prompt"), text(question, "kind"),
                            Boolean.TRUE.equals(question.get("required")),
                            question.get("minutes") instanceof Number n ? n.intValue() : 0,
                            question.get("probes") instanceof List<?> probes
                                    ? probes.stream().map(String::valueOf).toList()
                                    : List.of()));
                }
                sections.add(new Section(text(section, "id"), text(section, "title"), List.copyOf(questions)));
            }
            modules.add(new Module(text(module, "id"), text(module, "title"),
                    Boolean.TRUE.equals(module.get("optional")), List.copyOf(sections)));
        }
        return new InterviewForm(text(form, "role"), text(form, "formVersion"), text(form, "title"),
                List.copyOf(modules));
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> maps(Map<String, Object> parent, String key) {
        if (!(parent.get(key) instanceof List<?> list)) {
            throw new IllegalArgumentException("form.json has no '" + key + "' list");
        }
        return list.stream().map(entry -> {
            if (!(entry instanceof Map<?, ?> map)) {
                throw new IllegalArgumentException("form.json '" + key + "' holds a non-object: " + entry);
            }
            return (Map<String, Object>) map;
        }).toList();
    }

    private static String text(Map<String, Object> map, String key) {
        if (!(map.get(key) instanceof String value)) {
            throw new IllegalArgumentException("form.json entry has no '" + key + "': " + map);
        }
        return value;
    }
}
