import { createContext, useCallback, useContext, useState, ReactNode } from "react";

export interface RecentTask {
  id: string;
  label: string;
  status: "success" | "error" | "running";
  timestamp: string;
}

interface TasksContextValue {
  tasks: RecentTask[];
  pushTask: (label: string, status: RecentTask["status"]) => void;
}

const TasksContext = createContext<TasksContextValue | undefined>(undefined);

export function TasksProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<RecentTask[]>([]);

  const pushTask = useCallback((label: string, status: RecentTask["status"]) => {
    setTasks((prev) =>
      [
        { id: crypto.randomUUID(), label, status, timestamp: new Date().toLocaleTimeString() },
        ...prev,
      ].slice(0, 50)
    );
  }, []);

  return <TasksContext.Provider value={{ tasks, pushTask }}>{children}</TasksContext.Provider>;
}

export function useTasks(): TasksContextValue {
  const ctx = useContext(TasksContext);
  if (!ctx) throw new Error("useTasks deve essere usato dentro TasksProvider");
  return ctx;
}
