import { parseArgs, startStaticServer } from "../scripts/static-server.mjs";

if (!process.env.SESSION_API_KEY) throw new Error("SESSION_API_KEY fehlt");
const config = parseArgs(["--host", "0.0.0.0", "--port", "8000"]);
config.sessionApiKey = process.env.SESSION_API_KEY;
// Der Host-Port ist nur an Loopback gebunden; Zugriff erfolgt privat über Serve.
config.allowLanSessionKey = true;
config.routes = {
  "/cliscade": "http://cliscade:18002",
  "/api/automation": "http://automation:8000",
  ...Object.fromEntries(
    [
      "/api",
      "/sockets",
      "/server_info",
      "/alive",
      "/health",
      "/ready",
      "/openapi.json",
    ].map((path) => [path, "http://agent-server:8000"]),
  ),
};
config.runtimeServicesInfo = {
  mode: "cliscade-compose",
  services: {
    agent_server: { url_from_agent: "http://agent-server:8000" },
    ingress: { url_from_agent: "http://canvas:8000" },
    frontend: { kind: "static", url_from_agent: "http://canvas:8000" },
    automation: {
      url_from_agent: "http://automation:8000",
      api_prefix: "/api/automation",
      auth_env_var: "OPENHANDS_AUTOMATION_API_KEY",
    },
  },
};
await startStaticServer(config);
