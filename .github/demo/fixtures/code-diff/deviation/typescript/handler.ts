class Handler {
  submit(ctx: unknown, request: unknown): unknown {
    return this.anthropic.assess(ctx, request);
  }
}
