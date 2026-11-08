# Fluxor Local API. Build context: server/ (docker-compose.yml does this).
FROM eclipse-temurin:25-jdk AS build
WORKDIR /src
COPY . .
RUN --mount=type=cache,target=/root/.m2 ./mvnw -q -B -DskipTests package

FROM eclipse-temurin:25-jre
RUN useradd --system --uid 10001 --create-home fluxor
WORKDIR /app
COPY --from=build /src/apps/fluxor-local/target/quarkus-app/ /app/
USER fluxor
# The container listens on every interface; docker-compose publishes the port on 127.0.0.1 only.
ENV FLUXOR_LOCAL_HOST=0.0.0.0 \
    FLUXOR_LOCAL_PORT=18191 \
    JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=60"
EXPOSE 18191
ENTRYPOINT ["java", "-jar", "/app/quarkus-run.jar"]
