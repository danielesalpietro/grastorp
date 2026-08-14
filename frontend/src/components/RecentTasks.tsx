import { useTasks } from "../context/TasksContext";

export function RecentTasks() {
  const { tasks } = useTasks();

  return (
    <div className="recent-tasks">
      <div className="recent-tasks__header">Recent Tasks</div>
      {tasks.length === 0 ? (
        <div className="recent-tasks__empty">Nessuna attività recente</div>
      ) : (
        <table className="grid">
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td style={{ width: 90 }}>
                  <span className={`badge badge--${t.status === "success" ? "running" : t.status === "error" ? "error" : "creating"}`}>
                    {t.status}
                  </span>
                </td>
                <td>{t.label}</td>
                <td style={{ width: 100, color: "var(--text-muted)" }}>{t.timestamp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
