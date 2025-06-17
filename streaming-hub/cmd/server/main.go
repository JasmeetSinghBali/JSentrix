// entrypoint for the streaming-hub microservice.
// initializes the Fiber app, sets up routes, and starts the server.
package main

import (
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/config"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/delivery/http"
)

func main() {
	cfg := config.Load()
	app := http.NewFiberApp(cfg)
	app.Listen(cfg.Port)
}
