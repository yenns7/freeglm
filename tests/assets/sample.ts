interface TaskConfig {
  name: string;
  priority: "low" | "medium" | "high";
  timeout?: number;
  retries?: number;
}

interface TaskResult<T> {
  success: boolean;
  data?: T;
  error?: string;
  duration: number;
}

class TaskQueue {
  private queue: Array<{ config: TaskConfig; handler: () => Promise<unknown> }> = [];
  private running = 0;
  private readonly concurrency: number;

  constructor(concurrency = 4) {
    this.concurrency = concurrency;
  }

  enqueue<T>(config: TaskConfig, handler: () => Promise<T>): Promise<TaskResult<T>> {
    return new Promise((resolve) => {
      this.queue.push({
        config,
        handler: async () => {
          const start = Date.now();
          const retries = config.retries ?? 3;

          for (let attempt = 0; attempt <= retries; attempt++) {
            try {
              const data = await Promise.race([
                handler(),
                this.createTimeout(config.timeout ?? 30000),
              ]) as T;

              resolve({ success: true, data, duration: Date.now() - start });
              return;
            } catch (err) {
              if (attempt === retries) {
                resolve({
                  success: false,
                  error: err instanceof Error ? err.message : String(err),
                  duration: Date.now() - start,
                });
              }
            }
          }
        },
      });
      this.processNext();
    });
  }

  private async processNext(): Promise<void> {
    if (this.running >= this.concurrency || this.queue.length === 0) return;

    const sorted = this.queue.sort((a, b) => {
      const priority = { high: 0, medium: 1, low: 2 };
      return priority[a.config.priority] - priority[b.config.priority];
    });

    const task = sorted.shift()!;
    this.running++;

    try {
      await task.handler();
    } finally {
      this.running--;
      this.processNext();
    }
  }

  private createTimeout(ms: number): Promise<never> {
    return new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Timeout after ${ms}ms`)), ms)
    );
  }

  get pending(): number {
    return this.queue.length;
  }

  get active(): number {
    return this.running;
  }
}

export { TaskQueue, TaskConfig, TaskResult };
