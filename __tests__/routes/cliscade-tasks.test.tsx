import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { vi, describe, it, expect } from "vitest";
import CliscadeTasks from "#/routes/cliscade-tasks";
import { cliscadeRequest } from "#/api/cliscade-service";
import { beadsTaskTree } from "#/utils/beads-task-tree";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
vi.mock("#/api/cliscade-service", async (original) => ({
  ...(await original<typeof import("#/api/cliscade-service")>()),
  cliscadeRequest: vi.fn(),
}));
vi.mock("#/components/shared/navigation-link", () => ({
  NavigationLink: ({
    to,
    children,
  }: {
    to: string;
    children: React.ReactNode;
  }) => <a href={to}>{children}</a>,
}));

describe("CLIScade tasks", () => {
  it("hands the selected task and source attempt to the selected ACP agent", async () => {
    vi.mocked(cliscadeRequest).mockImplementation(async (path, body) => {
      if (path.endsWith("/probe"))
        return { discovery: { available_models: [], error: null } };
      if (body) return {};
      if (path === "/projects") return [{ id: "demo", beads: true }];
      if (path === "/agents") return [{ id: "codex" }, { id: "kiro" }];
      if (path.includes("/consensus?")) return [];
      if (path.endsWith("/tasks"))
        return [
          { id: "cn-1", title: "Implementierung", status: "open", priority: 2 },
        ];
      if (path.startsWith("/attempts/"))
        return {
          id: "a1",
          agent: "codex",
          status: "completed",
          created_at: "2026-10-16T08:00:00Z",
          session_id: "s1",
        };
      return [{ id: "a1" }];
    });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <MemoryRouter initialEntries={["/tasks?project=demo&task=cn-1"]}>
          <CliscadeTasks />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await screen.findByRole("button", { name: "CLISCADE$HANDOFF" });
    fireEvent.change(await screen.findByLabelText("CLISCADE$AGENT"), {
      target: { value: "kiro" },
    });
    fireEvent.click(screen.getByRole("button", { name: "CLISCADE$HANDOFF" }));
    await waitFor(() =>
      expect(cliscadeRequest).toHaveBeenCalledWith(
        "/projects/demo/attempts",
        {
          task_id: "cn-1",
          agent_id: "kiro",
          source_id: "a1",
          request_key: expect.any(String),
        },
        undefined,
      ),
    );
    fireEvent.click(screen.getByRole("checkbox", { name: "codex" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "kiro" }));
    fireEvent.click(
      screen.getByRole("button", { name: "CLISCADE$START_CONSENSUS" }),
    );
    await waitFor(() =>
      expect(cliscadeRequest).toHaveBeenCalledWith("/projects/demo/consensus", {
        task_id: "cn-1",
        agents: ["codex", "kiro"],
      }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "CLISCADE$CREATE_SCHEDULE" }),
    );
    await waitFor(() =>
      expect(cliscadeRequest).toHaveBeenCalledWith(
        "/projects/demo/tasks/cn-1/schedule",
        { cron: "0 9 * * 1-5", timezone: "Europe/Berlin", agent_id: "kiro" },
      ),
    );
  });

  it("starts native OpenHands with a discovered model and resets the choice on agent change", async () => {
    vi.mocked(cliscadeRequest).mockClear();
    vi.mocked(cliscadeRequest).mockImplementation(async (path, body) => {
      if (path.endsWith("/probe"))
        return {
          discovery: {
            current_model_id: path.includes("openhands")
              ? "openai/c1"
              : "cli-default",
            available_models: (path.includes("openhands")
              ? ["openai/c1", "openai/ant"]
              : ["cli-model"]
            ).map((model_id) => ({ model_id })),
            error: null,
          },
        };
      if (body) return {};
      if (path === "/projects") return [{ id: "demo", beads: true }];
      if (path === "/agents")
        return [
          { id: "openhands", model: "openai/c1", transport: "openhands" },
          { id: "kiro" },
        ];
      if (path.endsWith("/tasks"))
        return [{ id: "cn-1", title: "Task", status: "open", priority: 2 }];
      return [];
    });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <MemoryRouter initialEntries={["/tasks?project=demo&task=cn-1"]}>
          <CliscadeTasks />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    fireEvent.change(await screen.findByLabelText("CLISCADE$AGENT"), {
      target: { value: "openhands" },
    });
    await waitFor(() =>
      expect(
        document.querySelector('datalist option[value="openai/ant"]'),
      ).toBeTruthy(),
    );
    fireEvent.change(screen.getByLabelText("CLISCADE$MODEL"), {
      target: { value: "openai/ant" },
    });
    fireEvent.click(screen.getByRole("button", { name: "CLISCADE$START" }));
    await waitFor(() =>
      expect(cliscadeRequest).toHaveBeenCalledWith(
        "/projects/demo/attempts",
        {
          task_id: "cn-1",
          agent_id: "openhands",
          model: "openai/ant",
          request_key: expect.any(String),
        },
        undefined,
      ),
    );
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "CLISCADE$START" }),
      ).toBeEnabled(),
    );
    fireEvent.change(screen.getByLabelText("CLISCADE$AGENT"), {
      target: { value: "kiro" },
    });
    await waitFor(() =>
      expect(
        document.querySelector('datalist option[value="cli-model"]'),
      ).toBeTruthy(),
    );
    expect(screen.getByLabelText("CLISCADE$MODEL")).toHaveValue("");
    expect(
      document.querySelector('datalist option[value="openai/ant"]'),
    ).toBeNull();
    fireEvent.change(screen.getByLabelText("CLISCADE$AGENT"), {
      target: { value: "auto" },
    });
    expect(screen.queryByLabelText("CLISCADE$MODEL")).not.toBeInTheDocument();
  });

  it("orders children under their canonical parent and keeps cyclic input visible", () => {
    const tasks = [
      {
        id: "child",
        parent: "root",
        title: "Child",
        status: "open",
        priority: 0,
      },
      { id: "root", title: "Root", status: "open", priority: 2 },
      {
        id: "cycle",
        parent: "cycle",
        title: "Cycle",
        status: "open",
        priority: 3,
      },
    ];
    expect(
      beadsTaskTree(tasks).map(({ task, depth }) => [task.id, depth]),
    ).toEqual([
      ["root", 0],
      ["child", 1],
      ["cycle", 0],
    ]);
  });
});

describe("CLIScade isolation", () => {
  it("shows an attempt that wrote outside its workspace", async () => {
    vi.mocked(cliscadeRequest).mockImplementation(async (path) => {
      if (path.endsWith("/probe"))
        return { discovery: { available_models: [], error: null } };
      if (path === "/projects") return [{ id: "demo", beads: true }];
      if (path === "/agents") return [{ id: "codex" }];
      if (path.includes("/consensus?")) return [];
      if (path.endsWith("/tasks"))
        return [{ id: "cn-2", title: "Isolation", status: "open" }];
      if (path.includes("/attempts?task_id="))
        return [{ id: "a9", status: "completed" }];
      if (path.startsWith("/attempts/"))
        return {
          id: "a9",
          agent: "openhands",
          model: "openai/c1",
          task_id: "cn-2",
          session_id: "s9",
          status: "completed",
          created_at: "2026-10-18T08:00:00Z",
          source_id: null,
          checkpoint: {
            schema_version: 1,
            task: { id: "cn-2", title: "Isolation", status: "open" },
            git: {
              revision: "859f18f",
              status: "",
              diff: "",
              diff_truncated: false,
            },
            verified_checks: [],
            agent_claims: [],
            decisions: [],
            open_steps: [],
            isolation: {
              ok: false,
              changed_projects: ["ysamjo--userscripts"],
              scope: "git HEAD and status of registered projects",
            },
          },
          error: null,
        };
      return [];
    });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <MemoryRouter initialEntries={["/tasks?project=demo&task=cn-2"]}>
          <CliscadeTasks />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe(
      "CLISCADE$ISOLATION_VIOLATION: ysamjo--userscripts",
    );
  });
});

describe("CLIScade model choice", () => {
  it("sends the chosen model per consensus participant", async () => {
    vi.mocked(cliscadeRequest).mockImplementation(async (path) => {
      if (path.endsWith("/probe"))
        return { discovery: { available_models: [], error: null } };
      if (path === "/projects") return [{ id: "demo", beads: true }];
      if (path === "/agents") return [{ id: "codex" }, { id: "kiro" }];
      if (path.includes("/consensus?")) return [];
      if (path.endsWith("/tasks"))
        return [{ id: "cn-3", title: "Konsens", status: "open" }];
      if (path.includes("/attempts?task_id=")) return [];
      return [];
    });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <MemoryRouter initialEntries={["/tasks?project=demo&task=cn-3"]}>
          <CliscadeTasks />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    fireEvent.click(await screen.findByRole("checkbox", { name: "codex" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "kiro" }));
    fireEvent.change(screen.getByLabelText("CLISCADE$MODEL kiro"), {
      target: { value: "kiro/fast" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "CLISCADE$START_CONSENSUS" }),
    );
    await waitFor(() =>
      expect(cliscadeRequest).toHaveBeenCalledWith("/projects/demo/consensus", {
        task_id: "cn-3",
        agents: ["codex", "kiro"],
        models: { kiro: "kiro/fast" },
      }),
    );
  });

  it("sends the schedule with a model when one is chosen", async () => {
    vi.mocked(cliscadeRequest).mockImplementation(async (path) => {
      if (path.endsWith("/probe"))
        return { discovery: { available_models: [], error: null } };
      if (path === "/projects") return [{ id: "demo", beads: true }];
      if (path === "/agents") return [{ id: "codex" }];
      if (path.includes("/consensus?")) return [];
      if (path.endsWith("/tasks"))
        return [{ id: "cn-4", title: "Zeitplan", status: "open" }];
      if (path.includes("/attempts?task_id=")) return [];
      return [];
    });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <MemoryRouter initialEntries={["/tasks?project=demo&task=cn-4"]}>
          <CliscadeTasks />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    fireEvent.change(await screen.findByLabelText("CLISCADE$SCHEDULE_MODEL"), {
      target: { value: "openai/c1" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "CLISCADE$CREATE_SCHEDULE" }),
    );
    await waitFor(() =>
      expect(cliscadeRequest).toHaveBeenCalledWith(
        "/projects/demo/tasks/cn-4/schedule",
        {
          cron: "0 9 * * 1-5",
          timezone: "Europe/Berlin",
          agent_id: "auto",
          model: "openai/c1",
        },
      ),
    );
  });
});
