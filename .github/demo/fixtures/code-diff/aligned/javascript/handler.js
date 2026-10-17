class Handler {
  submit(ctx, request) {
    const job = this.jobs.enqueue(ctx, request);
    return job.id;
  }
}
