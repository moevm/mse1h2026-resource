FROM golang:1.25 AS builder
ARG CGO_ENABLED=0
WORKDIR /app

COPY go.mod ./
RUN go mod download
COPY . .
RUN go build

FROM scratch
COPY --from=builder /app/golang_app /golang_app
USER 65532:65532
EXPOSE 8002
ENTRYPOINT ["/golang_app"]
