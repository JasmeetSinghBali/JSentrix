// @title           Streaming Hub API
// @version         1.0
// @description     Real-time log/event streaming microservice for MCP/Electron.
// @contact.name    Jasmeet Singh Bali
// @contact.email   jasmeetbali.dev.2021@gmail.com
// @host            localhost:4001
// @BasePath        /
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
