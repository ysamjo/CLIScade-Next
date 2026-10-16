import { getAgentServerClientOptions } from "./agent-server-client-options";

export const CLISCADE_PATH = "/tasks";
const CLISCADE_API = "/cliscade/v1";
const SESSION_KEY_HEADER = "X-Session-API-Key";

export interface BeadsTask {
  id: string;
  title: string;
  description?: string;
  acceptance_criteria?: string;
  priority: number;
  status: string;
  assignee?: string;
  parent?: string;
  dependencies?: { id: string; title?: string; dependency_type?: string }[];
}

export interface TaskCheckpoint {
  schema_version: number;
  task: BeadsTask;
  git: {
    revision: string;
    status: string;
    diff: string;
    diff_truncated: boolean;
  };
  verified_checks: {
    command: string;
    exit_code: number;
    verification: string;
  }[];
  agent_claims: unknown[];
  decisions: string[];
  open_steps: string[];
}

export interface TaskAttempt {
  id: string;
  agent: string;
  task_id: string;
  session_id: string | null;
  status: string;
  created_at: string;
  source_id: string | null;
  route_trace?: { agent: string; reason: string }[];
  checkpoint: TaskCheckpoint | null;
  error: string | null;
}

export interface TaskAgent {
  id: string;
  command: string[];
  model: string | null;
  live_verified: boolean;
}

// CLIScade is a separate same-origin service, not an Agent Server API.
export async function cliscadeRequest<T>(
  path: string,
  body?: object,
  method?: string,
): Promise<T> {
  const { apiKey } = getAgentServerClientOptions();
  const response = await fetch(`${CLISCADE_API}${path}`, {
    method: method ?? (body ? "POST" : "GET"),
    headers: {
      [SESSION_KEY_HEADER]: apiKey ?? "",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    cache: "no-store",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(
      typeof error?.detail === "string"
        ? error.detail
        : `HTTP ${response.status}`,
    );
  }
  return response.json() as Promise<T>;
}

export const projectTaskPath = (project: string) =>
  `/projects/${encodeURIComponent(project)}/tasks`;
export const projectAttemptPath = (project: string) =>
  `/projects/${encodeURIComponent(project)}/attempts`;
