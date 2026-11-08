package com.javadaba.contexts.fluxor.infrastructure.adapters.inbound;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.ExceptionMapper;
import jakarta.ws.rs.ext.Provider;

import java.util.LinkedHashMap;
import java.util.Map;

/** Maps every {@link FluxorException} to the {@code httpStatus} set at its throw site -- same
 *  pattern as {@code SocialExceptionMapper}: the exception itself already carries the right
 *  status (see {@code TaskBacklogService}/{@code TaskStateValidator}), this is a one-line
 *  pass-through, not a classification table. {@code task_not_found}/{@code flow_not_found}/{@code
 *  run_not_found} (404) cover both a truly missing row AND one belonging to another account
 *  (never 403, never reveals existence). */
@Provider
public class FluxorExceptionMapper implements ExceptionMapper<FluxorException> {

    @Override
    public Response toResponse(FluxorException exception) {
        // Typed, because a route that produces bytes (a harness blob) must still answer errors as JSON.
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("error", exception.code());
        body.put("message", exception.getMessage() == null ? exception.code() : exception.getMessage());
        if (!exception.problems().isEmpty()) {
            body.put("problems", exception.problems());
        }
        return Response.status(exception.httpStatus()).type(MediaType.APPLICATION_JSON).entity(body).build();
    }
}
