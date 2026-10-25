package com.nocheat.repository;

import com.nocheat.model.Event;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface EventRepository extends JpaRepository<Event, UUID> {
    List<Event> findBySessionIdOrderByServerTsAsc(String sessionId);
}
