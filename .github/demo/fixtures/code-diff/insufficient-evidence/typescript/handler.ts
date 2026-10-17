class Handler {
  submit(ctx: unknown, request: unknown): unknown {
    return this.assessments.run(ctx, request);
  }
}
