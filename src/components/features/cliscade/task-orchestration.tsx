import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import {
  cliscadeRequest,
  projectTaskPath,
  type TaskAgent,
  type TaskAttempt,
} from "#/api/cliscade-service";
import { BrandButton } from "#/components/features/settings/brand-button";
import { CLISCADE_QUERY_KEYS } from "#/hooks/query/query-keys";

interface ConsensusRun {
  id: string;
  status: string;
  attempts: TaskAttempt[];
  result: {
    patch_agreement: boolean;
    correctness_verified: boolean;
    results: unknown[];
  };
}

export function TaskOrchestration({
  project,
  taskId,
  agents,
  agent,
  disabled,
}: {
  project: string;
  taskId: string;
  agents: TaskAgent[];
  agent: string;
  disabled: boolean;
}) {
  const { t } = useTranslation("openhands");
  const cache = useQueryClient();
  const [participants, setParticipants] = useState<string[]>([]);
  const [cron, setCron] = useState("0 9 * * 1-5");
  const [timezone, setTimezone] = useState("Europe/Berlin");
  const [scheduled, setScheduled] = useState(false);
  const [backupVerified, setBackupVerified] = useState(false);
  const runs = useQuery({
    queryKey: [...CLISCADE_QUERY_KEYS.all, "consensus", project, taskId],
    queryFn: () =>
      cliscadeRequest<ConsensusRun[]>(
        `/projects/${encodeURIComponent(project)}/consensus?task_id=${encodeURIComponent(taskId)}`,
      ),
    refetchInterval: 5000,
  });
  const change = useMutation({
    mutationFn: ({ path, body }: { path: string; body: object }) =>
      cliscadeRequest(path, body),
    onSuccess: () =>
      cache.invalidateQueries({ queryKey: CLISCADE_QUERY_KEYS.all }),
  });
  const schedule = (event: FormEvent) => {
    event.preventDefault();
    setScheduled(false);
    change.mutate(
      {
        path: `${projectTaskPath(project)}/${encodeURIComponent(taskId)}/schedule`,
        body: { cron, timezone, agent_id: agent },
      },
      { onSuccess: () => setScheduled(true) },
    );
  };
  return (
    <section className="mt-4 space-y-3 border-t border-border pt-4">
      <BrandButton
        className="min-h-11"
        type="button"
        variant="secondary"
        isDisabled={change.isPending}
        onClick={() => {
          setBackupVerified(false);
          change.mutate(
            {
              path: `/projects/${encodeURIComponent(project)}/backups`,
              body: {},
            },
            { onSuccess: () => setBackupVerified(true) },
          );
        }}
      >
        {t(I18nKey.CLISCADE$BACKUP)}
      </BrandButton>
      {backupVerified && (
        <p role="status">{t(I18nKey.CLISCADE$BACKUP_VERIFIED)}</p>
      )}
      <h3 className="font-semibold">{t(I18nKey.CLISCADE$ORCHESTRATION)}</h3>
      {(change.error ?? runs.error) && (
        <p role="alert">{(change.error ?? runs.error)?.message}</p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          change.mutate({
            path: `/projects/${encodeURIComponent(project)}/consensus`,
            body: { task_id: taskId, agents: participants },
          });
        }}
      >
        <fieldset disabled={disabled || change.isPending}>
          <legend>{t(I18nKey.CLISCADE$CONSENSUS_AGENTS)}</legend>
          <div className="flex flex-wrap gap-2">
            {agents.map((item) => (
              <label
                key={item.id}
                className="flex min-h-11 items-center gap-2 rounded border border-border px-3"
              >
                <input
                  type="checkbox"
                  checked={participants.includes(item.id)}
                  onChange={(event) =>
                    setParticipants((current) =>
                      event.target.checked
                        ? [...current, item.id]
                        : current.filter((id) => id !== item.id),
                    )
                  }
                />
                {item.id}
              </label>
            ))}
          </div>
          <BrandButton
            className="mt-2 min-h-11"
            type="submit"
            variant="secondary"
            isDisabled={
              participants.length < 2 ||
              participants.length > 4 ||
              disabled ||
              change.isPending
            }
          >
            {t(I18nKey.CLISCADE$START_CONSENSUS)}
          </BrandButton>
        </fieldset>
      </form>
      <p className="text-sm text-muted">{t(I18nKey.CLISCADE$CONSENSUS_NOTE)}</p>
      {runs.data?.map((run) => (
        <article key={run.id} className="rounded border border-border p-3">
          <p className="break-all">
            {run.status} · {run.id}
          </p>
          <p>
            {t(
              run.result.patch_agreement
                ? I18nKey.CLISCADE$PATCH_AGREEMENT
                : I18nKey.CLISCADE$PATCH_DIFFERENCE,
            )}
          </p>
          <details>
            <summary className="min-h-11 cursor-pointer">
              {t(I18nKey.CLISCADE$CONSENSUS_RESULTS)}
            </summary>
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-all text-xs">
              {JSON.stringify(run.result, null, 2)}
            </pre>
          </details>
          <BrandButton
            className="min-h-11"
            type="button"
            variant="secondary"
            isDisabled={
              change.isPending ||
              ["completed", "incomplete"].includes(run.status)
            }
            onClick={() =>
              change.mutate({ path: `/consensus/${run.id}/cancel`, body: {} })
            }
          >
            {t(I18nKey.CLISCADE$CANCEL)}
          </BrandButton>
        </article>
      ))}
      <form onSubmit={schedule} className="space-y-2">
        <label className="block">
          {t(I18nKey.CLISCADE$CRON)}
          <input
            required
            className="min-h-11 w-full rounded border border-border bg-canvas-base p-2"
            value={cron}
            onChange={(event) => setCron(event.target.value)}
          />
        </label>
        <label className="block">
          {t(I18nKey.CLISCADE$TIMEZONE)}
          <input
            required
            className="min-h-11 w-full rounded border border-border bg-canvas-base p-2"
            value={timezone}
            onChange={(event) => setTimezone(event.target.value)}
          />
        </label>
        <BrandButton
          className="min-h-11"
          type="submit"
          variant="secondary"
          isDisabled={disabled || change.isPending}
        >
          {t(I18nKey.CLISCADE$CREATE_SCHEDULE)}
        </BrandButton>
        {scheduled && <p role="status">{t(I18nKey.CLISCADE$SCHEDULED)}</p>}
        <a href="/automations" className="flex min-h-11 items-center underline">
          {t(I18nKey.CLISCADE$MANAGE_SCHEDULES)}
        </a>
      </form>
    </section>
  );
}
