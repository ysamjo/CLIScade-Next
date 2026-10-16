import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { BrandButton } from "#/components/features/settings/brand-button";
import { cliscadeRequest } from "#/api/cliscade-service";
import { CLISCADE_QUERY_KEYS } from "#/hooks/query/query-keys";
import { I18nKey } from "#/i18n/declaration";

const LOGIN_AGENTS = ["codex", "claude-code", "opencode", "kiro"] as const;
const POLL_MS = 3000;
const CONTROL =
  "min-h-11 w-full rounded-lg border border-border bg-canvas-base p-2";
interface LoginState {
  id?: string;
  state: "idle" | "pending" | "completed" | "failed" | "cancelled" | "expired";
  mode: "code" | "device";
  connected?: boolean;
  available?: boolean;
  url?: string | null;
  user_code?: string | null;
}

export function AgentLogin() {
  const { t } = useTranslation("openhands");
  const cache = useQueryClient();
  const [agent, setAgent] = useState<string>(LOGIN_AGENTS[0]);
  const [code, setCode] = useState("");
  const path = `/agents/${agent}/login`;
  const queryKey = CLISCADE_QUERY_KEYS.login(agent);
  const login = useQuery({
    queryKey,
    queryFn: () => cliscadeRequest<LoginState>(`/agents/${agent}/login`),
    refetchInterval: (query) =>
      query.state.data?.state === "pending" ? POLL_MS : false,
    retry: false,
  });
  const action = useMutation({
    mutationFn: ({
      suffix = "",
      body,
      method,
    }: {
      suffix?: string;
      body?: object;
      method?: string;
    }) => cliscadeRequest<LoginState>(`${path}${suffix}`, body, method),
    onSuccess: (state) => {
      setCode("");
      cache.setQueryData(queryKey, state);
      void cache.invalidateQueries({ queryKey });
      void cache.invalidateQueries({
        queryKey: CLISCADE_QUERY_KEYS.probe(agent),
      });
    },
  });
  const state = login.data;
  const pending = state?.state === "pending";
  const error = action.error ?? login.error;
  return (
    <section
      className="mb-5 min-w-0 space-y-3 rounded-xl border border-border bg-base-secondary p-4"
      aria-label={t(I18nKey.CLISCADE$LOGIN_TITLE)}
    >
      <h2 className="font-semibold">{t(I18nKey.CLISCADE$LOGIN_TITLE)}</h2>
      <p className="text-sm text-muted">{t(I18nKey.CLISCADE$LOGIN_INTRO)}</p>
      <label className="block max-w-sm">
        {t(I18nKey.CLISCADE$LOGIN_AGENT)}
        <select
          className={CONTROL}
          value={agent}
          disabled={action.isPending}
          onChange={(event) => {
            setAgent(event.target.value);
            setCode("");
            action.reset();
          }}
        >
          {LOGIN_AGENTS.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </label>
      <p role="status" aria-live="polite">
        {state?.connected
          ? t(I18nKey.CLISCADE$LOGIN_CONNECTED)
          : pending
            ? t(I18nKey.CLISCADE$LOGIN_PENDING)
            : t(I18nKey.CLISCADE$LOGIN_DISCONNECTED)}
      </p>
      {state?.available === false && (
        <p role="alert">{t(I18nKey.CLISCADE$LOGIN_MISSING)}</p>
      )}
      {state && ["failed", "expired", "cancelled"].includes(state.state) && (
        <p role="status">{t(I18nKey.CLISCADE$LOGIN_ENDED)}</p>
      )}
      {error && (
        <p role="alert" className="text-feedback-error">
          {error.message}
        </p>
      )}
      {pending && state?.url && (
        <div className="space-y-2">
          {state.user_code && (
            <p>
              <code className="select-all text-lg">{state.user_code}</code>
            </p>
          )}
          <a
            className="inline-flex min-h-11 items-center underline"
            href={state.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t(I18nKey.CLISCADE$LOGIN_OPEN)}
          </a>
          {state.mode === "code" && (
            <form
              className="max-w-xl space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                action.mutate({
                  suffix: "/code",
                  body: { id: state.id, code },
                });
              }}
            >
              <label className="block">
                {t(I18nKey.CLISCADE$LOGIN_CODE)}
                <input
                  className={CONTROL}
                  type="password"
                  autoComplete="one-time-code"
                  required
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                />
              </label>
              <BrandButton
                type="submit"
                variant="primary"
                isDisabled={!code || action.isPending}
              >
                {t(I18nKey.CLISCADE$LOGIN_SUBMIT)}
              </BrandButton>
            </form>
          )}
        </div>
      )}
      <div className="flex flex-wrap gap-3">
        {!pending && (
          <BrandButton
            type="button"
            variant="primary"
            isDisabled={action.isPending || state?.available === false}
            onClick={() => action.mutate({ body: {} })}
          >
            {t(I18nKey.CLISCADE$LOGIN_START)}
          </BrandButton>
        )}
        {pending && state?.id && (
          <BrandButton
            type="button"
            variant="secondary"
            isDisabled={action.isPending}
            onClick={() =>
              action.mutate({ suffix: `/${state.id}`, method: "DELETE" })
            }
          >
            {t(I18nKey.CLISCADE$CANCEL)}
          </BrandButton>
        )}
        <BrandButton
          type="button"
          variant="secondary"
          isDisabled={login.isFetching}
          onClick={() => {
            void login.refetch();
          }}
        >
          {t(I18nKey.CLISCADE$LOGIN_CHECK)}
        </BrandButton>
      </div>
    </section>
  );
}
