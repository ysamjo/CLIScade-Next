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
      if (body) return {};
      if (path === "/projects") return [{ id: "demo", beads: true }];
      if (path === "/agents") return [{ id: "codex" }, { id: "kiro" }];
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
        },
        undefined,
      ),
    );
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
