import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import {
  QueryClient,
  QueryClientProvider,
  focusManager,
} from "@tanstack/react-query";
import { vi, describe, it, expect } from "vitest";
import { AgentLogin } from "#/components/features/cliscade/agent-login";
import { cliscadeRequest } from "#/api/cliscade-service";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
vi.mock("#/api/cliscade-service", () => ({ cliscadeRequest: vi.fn() }));

function mount() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <AgentLogin />
    </QueryClientProvider>,
  );
}

describe("CLI account sign-in", () => {
  it.each(["success", "denied", "unavailable"])(
    "offers the full URL for copying when clipboard is %s",
    async (result) => {
      const url =
        "https://accounts.google.com/o/oauth2/v2/auth?state=test&redirect_uri=http%3A%2F%2F127.0.0.1%3A47407%2F";
      const writeText = vi.fn().mockImplementation(async () => {
        if (result === "denied") throw new Error("Permission denied");
      });
      const descriptor = Object.getOwnPropertyDescriptor(
        navigator,
        "clipboard",
      );
      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: result === "unavailable" ? undefined : { writeText },
      });
      try {
        vi.mocked(cliscadeRequest).mockImplementation(async (path) => ({
          state: path.includes("antigravity") ? "pending" : "idle",
          mode: "callback",
          url,
        }));
        mount();
        const input = (await screen.findByLabelText(
          "CLISCADE$LOGIN_URL",
        )) as HTMLInputElement;
        expect(input).toHaveValue(url);
        expect(input).toHaveAttribute("readonly");
        fireEvent.click(
          screen.getByRole("button", { name: "CLISCADE$LOGIN_COPY" }),
        );
        if (result === "success") {
          expect(
            await screen.findByText("CLISCADE$LOGIN_COPIED"),
          ).toBeInTheDocument();
          expect(writeText).toHaveBeenCalledWith(url);
        } else {
          expect(
            await screen.findByText("CLISCADE$LOGIN_COPY_MANUALLY"),
          ).toBeInTheDocument();
          expect(input).toHaveFocus();
          expect(input.selectionStart).toBe(0);
          expect(input.selectionEnd).toBe(url.length);
        }
        fireEvent.change(screen.getByLabelText("CLISCADE$LOGIN_AGENT"), {
          target: { value: "codebuddy" },
        });
        await waitFor(() =>
          expect(
            screen.queryByLabelText("CLISCADE$LOGIN_URL"),
          ).not.toBeInTheDocument(),
        );
        expect(
          screen.queryByText("CLISCADE$LOGIN_COPIED"),
        ).not.toBeInTheDocument();
        expect(
          screen.queryByText("CLISCADE$LOGIN_COPY_MANUALLY"),
        ).not.toBeInTheDocument();
      } finally {
        if (descriptor)
          Object.defineProperty(navigator, "clipboard", descriptor);
        else Reflect.deleteProperty(navigator, "clipboard");
      }
    },
  );

  it("shows link preparation and polls until the native provider URL is ready", async () => {
    let ready = false;
    vi.mocked(cliscadeRequest).mockImplementation(async () => ({
      state: "pending",
      mode: "callback",
      available: true,
      id: "slow-native-start",
      url: ready ? "https://accounts.google.com/o/oauth2/v2/auth" : null,
    }));
    mount();
    expect(
      await screen.findByText("CLISCADE$LOGIN_PREPARING"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "CLISCADE$LOGIN_OPEN" }),
    ).not.toBeInTheDocument();
    focusManager.setFocused(false);
    try {
      ready = true;
      expect(
        await screen.findByRole(
          "link",
          { name: "CLISCADE$LOGIN_OPEN" },
          { timeout: 6000 },
        ),
      ).toHaveAttribute("href", "https://accounts.google.com/o/oauth2/v2/auth");
      expect(
        screen.queryByText("CLISCADE$LOGIN_PREPARING"),
      ).not.toBeInTheDocument();
    } finally {
      focusManager.setFocused(undefined);
    }
  });
  it("prioritizes Antigravity and keeps CodeBuddy on its native browser flow", async () => {
    vi.mocked(cliscadeRequest).mockImplementation(async (path) => ({
      state: "pending",
      available: true,
      mode: path.includes("codebuddy") ? "browser" : "callback",
      id: "native-login",
      url: path.includes("codebuddy")
        ? "https://www.codebuddy.ai/login"
        : "https://accounts.google.com/o/oauth2/v2/auth",
    }));
    mount();
    const selector = screen.getByLabelText("CLISCADE$LOGIN_AGENT");
    expect(selector).toHaveValue("antigravity");
    expect(
      await screen.findByText("CLISCADE$LOGIN_ANTIGRAVITY"),
    ).toBeInTheDocument();
    expect(
      await screen.findByLabelText("CLISCADE$LOGIN_GENERIC_CALLBACK"),
    ).toBeInTheDocument();
    fireEvent.change(selector, { target: { value: "codebuddy" } });
    expect(
      await screen.findByText("CLISCADE$LOGIN_CODEBUDDY"),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "CLISCADE$LOGIN_OPEN" }),
      ).toHaveAttribute("href", "https://www.codebuddy.ai/login"),
    );
    expect(
      screen.queryByLabelText("CLISCADE$LOGIN_GENERIC_CALLBACK"),
    ).not.toBeInTheDocument();
  });

  it("starts device login without API keys, displays the challenge and cancels it", async () => {
    let state = {
      state: "idle",
      available: true,
      connected: false,
      mode: "device",
    };
    vi.mocked(cliscadeRequest).mockImplementation(
      async (path, body, method) => {
        if (method === "DELETE") state = { ...state, state: "cancelled" };
        else if (body)
          state = {
            ...state,
            state: "pending",
            id: "login-1",
            url: "https://auth.openai.com/codex/device",
            user_code: "ABCD-EFGH",
          } as typeof state;
        return state;
      },
    );
    mount();
    fireEvent.change(screen.getByLabelText("CLISCADE$LOGIN_AGENT"), {
      target: { value: "codex" },
    });
    fireEvent.click(
      await screen.findByRole("button", { name: "CLISCADE$LOGIN_START" }),
    );
    expect(await screen.findByText("ABCD-EFGH")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "CLISCADE$LOGIN_OPEN" }),
    ).toHaveAttribute("href", "https://auth.openai.com/codex/device");
    expect(
      screen.queryByLabelText("CLISCADE$LOGIN_CODE"),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "CLISCADE$CANCEL" }));
    await waitFor(() =>
      expect(cliscadeRequest).toHaveBeenCalledWith(
        "/agents/codex/login/login-1",
        undefined,
        "DELETE",
      ),
    );
  });

  it("sends Claude's one-time code to its own login and clears the code afterwards", async () => {
    vi.mocked(cliscadeRequest).mockImplementation(async (path, body) => {
      if (path.endsWith("/code"))
        return { state: "completed", connected: true, mode: "code" };
      if (path.includes("claude-code"))
        return {
          id: "claude-login",
          state: "pending",
          mode: "code",
          url: "https://claude.ai/oauth/authorize?state=test",
        };
      return { state: "idle", mode: "device", connected: false };
    });
    mount();
    fireEvent.change(screen.getByLabelText("CLISCADE$LOGIN_AGENT"), {
      target: { value: "claude-code" },
    });
    const input = await screen.findByLabelText("CLISCADE$LOGIN_CODE");
    fireEvent.change(input, { target: { value: "one-time-code" } });
    fireEvent.click(
      screen.getByRole("button", { name: "CLISCADE$LOGIN_SUBMIT" }),
    );
    await waitFor(() =>
      expect(cliscadeRequest).toHaveBeenCalledWith(
        "/agents/claude-code/login/code",
        { id: "claude-login", code: "one-time-code" },
        undefined,
      ),
    );
    fireEvent.change(screen.getByLabelText("CLISCADE$LOGIN_AGENT"), {
      target: { value: "kiro" },
    });
    expect(
      within(screen.getByRole("region")).queryByDisplayValue("one-time-code"),
    ).not.toBeInTheDocument();
  });
  it("opens each agent's own portal and submits Kiro's callback without forcing another identity provider", async () => {
    const started = new Set<string>();
    vi.mocked(cliscadeRequest).mockImplementation(async (path, body) => {
      if (body) started.add(path);
      const kiro = path.includes("kiro");
      return {
        state: started.has(path) ? "pending" : "idle",
        available: true,
        mode: kiro ? "callback" : "device",
        id: "native-login",
        url: kiro
          ? "https://app.kiro.dev/signin"
          : "https://opencode.ai/console/device",
      };
    });
    mount();
    fireEvent.change(screen.getByLabelText("CLISCADE$LOGIN_AGENT"), {
      target: { value: "opencode" },
    });
    expect(
      await screen.findByText("CLISCADE$LOGIN_OPENCODE"),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "CLISCADE$LOGIN_START" }),
    );
    expect(
      await screen.findByRole("link", { name: "CLISCADE$LOGIN_OPEN" }),
    ).toHaveAttribute("href", "https://opencode.ai/console/device");
    fireEvent.change(screen.getByLabelText("CLISCADE$LOGIN_AGENT"), {
      target: { value: "kiro" },
    });
    await screen.findByText("CLISCADE$LOGIN_KIRO");
    fireEvent.click(
      screen.getByRole("button", { name: "CLISCADE$LOGIN_START" }),
    );
    const callback = await screen.findByLabelText(
      "CLISCADE$LOGIN_GENERIC_CALLBACK",
    );
    expect(callback).toHaveAttribute("aria-describedby", "login-callback-help");
    const value = "http://localhost:3128/?code=one-time&state=native-state";
    fireEvent.change(callback, { target: { value } });
    fireEvent.click(
      screen.getByRole("button", { name: "CLISCADE$LOGIN_SUBMIT" }),
    );
    await waitFor(() =>
      expect(cliscadeRequest).toHaveBeenCalledWith(
        "/agents/kiro/login/code",
        { id: "native-login", code: value },
        undefined,
      ),
    );
  });
});
