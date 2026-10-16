import type { BeadsTask } from "#/api/cliscade-service";

export function beadsTaskTree(tasks: BeadsTask[]) {
  const ids = new Set(tasks.map((task) => task.id));
  const seen = new Set<string>();
  const result: { task: BeadsTask; depth: number }[] = [];
  const sorted = [...tasks].sort(
    (a, b) => a.priority - b.priority || a.id.localeCompare(b.id),
  );
  const visit = (task: BeadsTask, depth: number) => {
    if (seen.has(task.id)) return;
    seen.add(task.id);
    result.push({ task, depth });
    sorted
      .filter((child) => child.parent === task.id)
      .forEach((child) => visit(child, depth + 1));
  };
  sorted
    .filter((task) => !task.parent || !ids.has(task.parent))
    .forEach((task) => visit(task, 0));
  sorted.forEach((task) => visit(task, 0));
  return result;
}
