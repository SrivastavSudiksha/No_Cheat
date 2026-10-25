package com.nocheat.controller;

import com.nocheat.model.Event;
import com.nocheat.repository.EventRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/events")
public class EventController {

    private final EventRepository eventRepository;

    public EventController(EventRepository eventRepository) {
        this.eventRepository = eventRepository;
    }

    /**
     * Called by FastAPI detection service (service-to-service).
     * In production protect with API key or mTLS.
     */
    @PostMapping
    public ResponseEntity<Event> ingest(@RequestBody Map<String, Object> body) {
        Event e = new Event();
        e.setSessionId((String) body.get("session_id"));
        e.setType((String) body.get("type"));
        e.setSeverity(((Number) body.getOrDefault("severity", 0.5)).doubleValue());
        e.setConfidence(((Number) body.getOrDefault("confidence", 0.0)).doubleValue());
        e.setServerTs(Instant.now()); // always server time
        if (body.get("duration_ms") != null) {
            e.setDurationMs(((Number) body.get("duration_ms")).intValue());
        }
        e.setEvidenceUrl((String) body.get("evidence_url"));
        if (body.get("extra") != null) {
            e.setExtraJson(body.get("extra").toString());
        }

        // TODO: compute hash chain here
        Event saved = eventRepository.save(e);
        return ResponseEntity.ok(saved);
    }

    @GetMapping("/session/{sessionId}")
    public List<Event> bySession(@PathVariable String sessionId) {
        return eventRepository.findBySessionIdOrderByServerTsAsc(sessionId);
    }
}
