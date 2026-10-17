class Handler {
  submit(ctx: unknown, request: unknown): unknown {
    const job = this.jobs.enqueue(ctx, request);
    return job.id;
  }
}
