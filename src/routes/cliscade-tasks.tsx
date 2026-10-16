import { useState, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { BrandButton } from "#/components/features/settings/brand-button";
import { NavigationLink } from "#/components/shared/navigation-link";
import { CLISCADE_QUERY_KEYS } from "#/hooks/query/query-keys";
import {
  cliscadeRequest,
  projectTaskPath,
  projectAttemptPath,
  type BeadsTask,
  type TaskAttempt,
  type TaskAgent,
} from "#/api/cliscade-service";

import { beadsTaskTree } from "#/utils/beads-task-tree";

const CONTROL =
  "min-h-11 w-full rounded-lg border border-border bg-canvas-base p-2 text-base text-contrast";
const CARD = "min-w-0 rounded-xl border border-border bg-base-secondary p-4";
const PROJECT_PARAM = "project";
const TASK_PARAM = "task";
const POLL_MS = 5000;

export default function CliscadeTasks() {
  const { t } = useTranslation("openhands");
  const cache = useQueryClient();
  const [params, setParams] = useSearchParams();
  const project = params.get(PROJECT_PARAM) ?? "";
  const selected = params.get(TASK_PARAM) ?? "";
  const [agent, setAgent] = useState("codex");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [acceptance, setAcceptance] = useState("");
  const [priority, setPriority] = useState(2);
  const [parent, setParent] = useState("");
  const [dependency, setDependency] = useState("");
  const [editing, setEditing] = useState(false);
  const projects = useQuery({
    queryKey: CLISCADE_QUERY_KEYS.projects,
    queryFn: () =>
      cliscadeRequest<{ id: string; beads: boolean }[]>("/projects"),
  });
  const agents = useQuery({
    queryKey: CLISCADE_QUERY_KEYS.agents,
    queryFn: () => cliscadeRequest<TaskAgent[]>("/agents"),
  });
  const tasks = useQuery({
    queryKey: CLISCADE_QUERY_KEYS.tasks(project),
    queryFn: () => cliscadeRequest<BeadsTask[]>(projectTaskPath(project)),
    enabled: !!project,
  });
  const attempts = useQuery({
    queryKey: CLISCADE_QUERY_KEYS.attempts(project, selected),
    queryFn: async () => {
      const saved = await cliscadeRequest<TaskAttempt[]>(
        `${projectAttemptPath(project)}?task_id=${encodeURIComponent(selected)}`,
      );
      return Promise.all(
        saved.map((attempt) =>
          cliscadeRequest<TaskAttempt>(`/attempts/${attempt.id}`),
        ),
      );
    },
    enabled: !!project && !!selected,
    refetchInterval: POLL_MS,
  });
  const mutation = useMutation({
    mutationFn: ({
      path,
      body,
      method,
    }: {
      path: string;
      body?: object;
      method?: string;
    }) => cliscadeRequest(path, body, method),
    onSuccess: () =>
      cache.invalidateQueries({ queryKey: CLISCADE_QUERY_KEYS.all }),
  });
  const task = tasks.data?.find((item) => item.id === selected);
  const error =
    projects.error ??
    agents.error ??
    tasks.error ??
    attempts.error ??
    mutation.error;
  const pending = mutation.isPending;
  const chooseTask = (id: string) => {
    setEditing(false);
    setParams({ [PROJECT_PARAM]: project, [TASK_PARAM]: id });
  };
  const saveTask = (event: FormEvent) => {
    event.preventDefault();
    const body = {
      title,
      description,
      acceptance,
      priority,
      ...(!editing && parent ? { parent } : {}),
    };
    mutation.mutate(
      {
        path: editing
          ? `${projectTaskPath(project)}/${selected}`
          : projectTaskPath(project),
        body,
        method: editing ? "PATCH" : "POST",
      },
      {
        onSuccess: () => {
          setTitle("");
          setDescription("");
          setAcceptance("");
          setEditing(false);
        },
      },
    );
  };
  const start = (source_id?: string) =>
    mutation.mutate({
      path: projectAttemptPath(project),
      body: {
        task_id: selected,
        agent_id: agent,
        ...(source_id ? { source_id } : {}),
      },
    });

  return (
    <main
      className="min-h-0 flex-1 overflow-y-auto p-3 text-contrast sm:p-6"
      lang="de"
    >
      <header className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            {t(I18nKey.CLISCADE$TITLE)}
          </h1>
          <p className="mt-1 text-sm text-muted">{t(I18nKey.CLISCADE$INTRO)}</p>
        </div>
        <label className="w-full sm:w-72">
          {t(I18nKey.CLISCADE$PROJECT)}
          <select
            className={CONTROL}
            value={project}
            onChange={(e) => {
              setEditing(false);
              setParams({ [PROJECT_PARAM]: e.target.value });
            }}
          >
            <option value="">{t(I18nKey.CLISCADE$CHOOSE_PROJECT)}</option>
            {projects.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id}
              </option>
            ))}
          </select>
        </label>
      </header>
      {error && (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-status-error p-3"
        >
          {error.message}
        </p>
      )}
      {(projects.isLoading || tasks.isLoading) && (
        <p role="status">{t(I18nKey.CLISCADE$LOADING)}</p>
      )}
      <div className="grid min-w-0 gap-4 lg:grid-cols-3">
        <section className={CARD} aria-label={t(I18nKey.CLISCADE$TASKS)}>
          <h2 className="mb-3 font-semibold">{t(I18nKey.CLISCADE$TASKS)}</h2>
          <ul className="space-y-2">
            {beadsTaskTree(tasks.data ?? []).map(({ task: item, depth }) => (
              <li
                key={item.id}
                style={{ paddingInlineStart: Math.min(depth, 4) * 12 }}
              >
                <button
                  type="button"
                  aria-pressed={selected === item.id}
                  onClick={() => chooseTask(item.id)}
                  className={`min-h-11 w-full rounded-lg border p-3 text-left ${selected === item.id ? "border-primary bg-interactive-hover" : "border-border"}`}
                >
                  <span className="block break-words font-medium">
                    {item.title}
                  </span>
                  <span className="block text-sm text-muted">
                    {item.id} · {item.priority} · {item.status}
                  </span>
                  {item.assignee && (
                    <span className="block text-sm">{item.assignee}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          {project && (
            <form
              onSubmit={saveTask}
              className="mt-5 space-y-3 border-t border-border pt-4"
            >
              <h2 className="font-semibold">
                {t(editing ? I18nKey.CLISCADE$EDIT : I18nKey.CLISCADE$NEW_TASK)}
              </h2>
              <label className="block">
                {t(I18nKey.CLISCADE$TASK_TITLE)}
                <input
                  required
                  maxLength={500}
                  className={CONTROL}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <label className="block">
                {t(I18nKey.CLISCADE$DESCRIPTION)}
                <textarea
                  className={CONTROL}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </label>
              <label className="block">
                {t(I18nKey.CLISCADE$ACCEPTANCE)}
                <textarea
                  className={CONTROL}
                  value={acceptance}
                  onChange={(e) => setAcceptance(e.target.value)}
                />
              </label>
              <label className="block">
                {t(I18nKey.CLISCADE$PRIORITY)}
                <select
                  className={CONTROL}
                  value={priority}
                  onChange={(e) => setPriority(Number(e.target.value))}
                >
                  {[0, 1, 2, 3, 4].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              {!editing && (
                <label className="block">
                  {t(I18nKey.CLISCADE$PARENT)}
                  <select
                    className={CONTROL}
                    value={parent}
                    onChange={(e) => setParent(e.target.value)}
                  >
                    <option value="">{t(I18nKey.CLISCADE$NONE)}</option>
                    {tasks.data?.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.title}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <BrandButton type="submit" variant="primary" isDisabled={pending}>
                {t(I18nKey.CLISCADE$SAVE)}
              </BrandButton>
            </form>
          )}
        </section>
        <section
          className="min-w-0 space-y-4 lg:col-span-2"
          aria-label={t(I18nKey.CLISCADE$HISTORY)}
        >
          {task && (
            <div className={CARD}>
              <h2 className="text-xl font-semibold">{task.title}</h2>
              <p className="mt-2 whitespace-pre-wrap break-words">
                {task.description}
              </p>
              <h3 className="mt-3 font-semibold">
                {t(I18nKey.CLISCADE$ACCEPTANCE)}
              </h3>
              <p className="whitespace-pre-wrap break-words">
                {task.acceptance_criteria}
              </p>
              <div className="my-4 flex flex-wrap gap-2">
                <BrandButton
                  className="min-h-11"
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setTitle(task.title);
                    setDescription(task.description ?? "");
                    setAcceptance(task.acceptance_criteria ?? "");
                    setPriority(task.priority);
                    setEditing(true);
                  }}
                >
                  {t(I18nKey.CLISCADE$EDIT)}
                </BrandButton>
                <BrandButton
                  className="min-h-11"
                  type="button"
                  variant="secondary"
                  isDisabled={pending}
                  onClick={() =>
                    mutation.mutate({
                      path: `${projectTaskPath(project)}/${selected}`,
                      body: {
                        status: task.status === "closed" ? "open" : "closed",
                      },
                      method: "PATCH",
                    })
                  }
                >
                  {t(
                    task.status === "closed"
                      ? I18nKey.CLISCADE$REOPEN
                      : I18nKey.CLISCADE$CLOSE,
                  )}
                </BrandButton>
              </div>
              <label className="block">
                {t(I18nKey.CLISCADE$AGENT)}
                <select
                  className={CONTROL}
                  value={agent}
                  onChange={(e) => setAgent(e.target.value)}
                >
                  {agents.data?.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.id}
                    </option>
                  ))}
                </select>
              </label>
              <p className="my-2 text-sm text-muted">
                {t(I18nKey.CLISCADE$VERIFICATION_NOTE)}
              </p>
              <BrandButton
                className="min-h-11"
                type="button"
                variant="primary"
                isDisabled={pending || task.status === "closed"}
                onClick={() => start()}
              >
                {t(I18nKey.CLISCADE$START)}
              </BrandButton>
              <form
                className="mt-4 flex flex-wrap items-end gap-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  mutation.mutate({
                    path: `${projectTaskPath(project)}/${selected}/dependencies`,
                    body: { depends_on: dependency },
                  });
                }}
              >
                <label className="min-w-0 flex-1">
                  {t(I18nKey.CLISCADE$DEPENDENCY)}
                  <select
                    className={CONTROL}
                    required
                    value={dependency}
                    onChange={(e) => setDependency(e.target.value)}
                  >
                    <option value="">{t(I18nKey.CLISCADE$NONE)}</option>
                    {tasks.data
                      ?.filter((item) => item.id !== selected)
                      .map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.title}
                        </option>
                      ))}
                  </select>
                </label>
                <BrandButton
                  className="min-h-11"
                  type="submit"
                  variant="secondary"
                  isDisabled={pending}
                >
                  {t(I18nKey.CLISCADE$ADD)}
                </BrandButton>
              </form>
            </div>
          )}
          {attempts.data?.map((attempt) => (
            <article key={attempt.id} className={CARD}>
              <h3 className="font-semibold">
                {attempt.agent} · {attempt.status}
              </h3>
              <p className="break-all text-xs text-muted">{attempt.id}</p>
              <p className="text-sm text-muted">
                {new Date(attempt.created_at).toLocaleString()}
              </p>
              {attempt.error && <p role="alert">{attempt.error}</p>}
              <div className="my-3 flex flex-wrap gap-3">
                {attempt.session_id && (
                  <NavigationLink
                    className="min-h-11 py-2 underline"
                    to={`/conversations/${attempt.session_id}`}
                  >
                    {t(I18nKey.CLISCADE$SESSION)}
                  </NavigationLink>
                )}
                {["running", "submitted", "uncertain", "cancelling"].includes(
                  attempt.status,
                ) && (
                  <BrandButton
                    className="min-h-11"
                    type="button"
                    variant="secondary"
                    isDisabled={pending}
                    onClick={() =>
                      mutation.mutate({
                        path: `/attempts/${attempt.id}/cancel`,
                        body: {},
                      })
                    }
                  >
                    {t(I18nKey.CLISCADE$CANCEL)}
                  </BrandButton>
                )}
                {["completed", "failed", "cancelled"].includes(
                  attempt.status,
                ) && (
                  <BrandButton
                    className="min-h-11"
                    type="button"
                    variant="primary"
                    isDisabled={pending}
                    onClick={() => start(attempt.id)}
                  >
                    {t(I18nKey.CLISCADE$HANDOFF)}
                  </BrandButton>
                )}
              </div>
              {attempt.checkpoint && (
                <>
                  <details>
                    <summary className="min-h-11 cursor-pointer py-2">
                      {t(I18nKey.CLISCADE$GIT)}
                    </summary>
                    <p className="break-all text-xs">
                      {attempt.checkpoint.git.revision}
                    </p>
                    <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-all text-xs">
                      {attempt.checkpoint.git.status}
                      {attempt.checkpoint.git.diff}
                    </pre>
                    {attempt.checkpoint.git.diff_truncated && (
                      <p>{t(I18nKey.CLISCADE$TRUNCATED)}</p>
                    )}
                  </details>
                  <details>
                    <summary className="min-h-11 cursor-pointer py-2">
                      {t(I18nKey.CLISCADE$CHECKS)}
                    </summary>
                    <ul>
                      {attempt.checkpoint.verified_checks.map((check, i) => (
                        <li key={i} className="break-all text-sm">
                          {check.command} · {check.exit_code}
                        </li>
                      ))}
                    </ul>
                    <p className="text-sm text-muted">
                      {t(I18nKey.CLISCADE$RECEIPT_NOTE)}
                    </p>
                  </details>
                  <details>
                    <summary className="min-h-11 cursor-pointer py-2">
                      {t(I18nKey.CLISCADE$CHECKPOINT)}
                    </summary>
                    <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-all text-xs">
                      {JSON.stringify(attempt.checkpoint, null, 2)}
                    </pre>
                  </details>
                </>
              )}
            </article>
          ))}
          {!task && <p className={CARD}>{t(I18nKey.CLISCADE$CHOOSE_TASK)}</p>}
        </section>
      </div>
    </main>
  );
}
